from canlib import canlib, Frame
import time
import random
from random import randint
import threading
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import time as t
import json
import cantools
import datetime
import os

global compteur_10ms

#Send Id avec un cycle de 10ms
def send_mqtt_10ms():
    #--------------------------- Principe de fonctionnement -------------------------------
    # 1) Récupère les datas lues et mis en forme du dbc.
    # 2) Génère à chaque coup d'horloge, une trame pseudo aléatoire,
    # pour chaque entrée du dbc. Pour ce faire :
    #       a) Créer l'header de la trame (parti fixe)
    #       b) Créer la partie variable de la trame
    #           i  ) Génère des datas pseudos aléatoire via create_data()
    #           ii ) Converti les datas en bytes
    #           iii) Concatène les trames de chaque entrée du dbc en une unique trame
    # 3) Publish sur mqtt de la trame
    # 4) Fait un Backup des strucutres en json pour le debug
    # -------------------------------------------------------------------------------------
    
    # Init
    # compteur de la partie header 
    global compteur_10ms 
    # Var pour stocker les trames précédentes par id
    global trame_prev_per_id

    # compteur permettnat de faire varier le print des published pour voir si on ublie toujours
    global point_display 
    point_display = 0

    # Backup communication mqtt
    mqtt_backup = []
    # timer pour backup
    timer = 0
    # Compteur ms et epoch_s
    ms_ts = 0
    epoch_s = 0

    # Boucle inf, break que si on sauvegarde
    while True:
        try: 
            # --------- Init--------------
            can_msg = None
            trame = []
            # Backup des valeurs calculées pour les trames
            trame_concat_backup = []  
            # msg a publier sur mqtt
            msg_to_publish = []
            
            # ------- Créer le Header de la trame ------------
            # Nombre de trames
            nb_trames = len(list_10ms)
            # Timestamp
            old_epoch_s = epoch_s #mise en mémoire de l'epoch_s précédent, pour le raz des ms
            epoch_s = int(t.time())
            
            # Concaténation du topic header
            header = nb_trames.to_bytes(1,'big') + epoch_s.to_bytes(4,'big') + compteur_10ms.to_bytes(1,'big')
            # Ajout de l'header à la trame finale
            msg_to_publish = header

            # ------ Créer la partie variable de la Trame ----
            #parcour les trames de la liste
            for el in list_10ms:
                #init
                list_data = []
                data_sorter = []
            
                #récupère les datas
                created_trame = create_data(el)  #Récupère la structure de la trame compressé généré alétoirement
                list_data = created_trame['list_data'] #uniquement les données de la trame
                data_sorter = created_trame['data_sorter'] #récup le data_sorter
                dlc = created_trame['dlc']

                #préparation des trames a envoyer
                # Create the id 
                id_compressed  = el["id_compressed"]

                # Create the ms timestamp
                ms_ts += random.randint(5,20)
                # reset ms si overflow ou si nouvelle seconde
                if ms_ts >= 9999 or old_epoch_s<epoch_s:
                    ms_ts = 0

                # Convert the data sorter
                data_sorter_bin = ''.join(map(str, data_sorter))  # Converti la liste binaire en une chaîne binaire
                data_sorter_int = int(data_sorter_bin, 2) # Converti en décimla
                
                # Compress the data part
                data_compressed =[] # Init
                data_sorter_real = data_sorter[-dlc:] #c'est le datasorter réel (ex: 111 au lieu de 0000 0011 si dlc=3)
                for index, octet in enumerate(data_sorter_real):
                    if octet=="1":
                        data_compressed.append(list_data[index])
                # Convert data compressed
                data = bytes(data_compressed)

                # Fabrique la trame concaténé
                new_concatened_trame = id_compressed.to_bytes(1,'big') + ms_ts.to_bytes(2,'big')+ data_sorter_int.to_bytes(1,'big') + data
                msg_to_publish = msg_to_publish + new_concatened_trame
                #trame.append(new_concatened_trame) #concatène les trames
                
                # Fabrique le back up de la trame
                trame_concat_backup.append({ 'position_and_id_compressed': id_compressed,'id': created_trame['id'],
                                     "id_hex":hex(created_trame['id']),'dlc': dlc,
                                     'sync': str(created_trame['sync']),'prev': str(created_trame['prev']),
                                     'data_brut': str(created_trame['list_data']), 
                                     'data_hexa':str([hex(x) for x in created_trame['list_data']]),
                                     'data_compressed' :str(data_compressed),
                                     'data_sorter_bin':data_sorter_bin, 
                                     'data_compressed_converted':str(data), 'trame_sended':str(new_concatened_trame) })
            
            # -----------------Fabrique la trame finale a envoyer--------------
            # envoi des trames
            mqtt_connection.publish(topic=TOPIC, payload= msg_to_publish, qos=mqtt.QoS.AT_LEAST_ONCE)

            # Update du compteur du header
            compteur_10ms = (compteur_10ms+1)%255
            
            # ----- fabrique le backup de la com mqtt -----
            # Full Backup
            mqtt_backup.append({'header':str(header), 'msg_mqtt':str(msg_to_publish),'trame_concat_backup':trame_concat_backup})
           
            # Small to compare with the payload of the subcriber          
            #mqtt_backup.append(str(msg_to_publish))
            
            # Fait varier le publish
            point_display = (point_display+1)%10
            print("Published" + point_display*".")
        except Exception as e:
            print (e)
            print("Not published ❌")
        
        #--------------Gestion timer et sauvegarde si besoin --------------------------
        # Count until save_count overflow
        timer +=1 
        if timer >= SAVE_COUNT and SAVE_ACTIVATED: #save toutes les min si sauveagrde activée
            try:
                save_json(mqtt_backup)
                print("Saved ✅")
                break
            except Exception as e:
                print (e)
                print("Not saved ❌")
                break

        time.sleep(1)

# Créer le data_sorter en fonction du dlc et de sync (si True alors data sorter = que des 1)
def create_data_sorter(dlc,sync):
    # init data_sorterfirst_sync
    data_sorter = ""
    #création data sorter en fonction du DLC
    #si trame de synchronisation que des 1, sinon aléatoire
    if(sync):
        for i in range (dlc):    
            data_sorter += "1" #car toutes les datas sont nouvelles
    else:
        # création du masque aélatoire
        for i in range (dlc):    
            data_sorter += str(random.choice([0, 1]))
        
    #mise du data_sorter sur 8 bits (rajout zero a gauche si besoin)
    data_sorter_8bit = data_sorter.zfill(8)
    return(data_sorter_8bit)

# génère des trames aléatoire
def create_data(trame):
    list_data = []
    return_struct =[]
    # init data_sorter
    data_sorter = ""
    #parcour les trames de la liste
    #génère data aléatoire pour chaque trame si sync vide ou si cpt =0
    if trame["sync"] == [] or compteur_10ms == 0:
        for octet in range (0,trame["dlc"]): 
            list_data.append(randint(0,255)) #génération trame
        trame["sync"] = list_data # la trame deviens alors la trame de synchro
        trame["prev"]= [] #trame prev est vide car elle nexiste pas et/ou plus
        
        # Get a data_sorter 
        data_sorter = create_data_sorter(trame["dlc"],True)
    #sinon 
    else :
        
        data_sorter = create_data_sorter(trame["dlc"],False)
        # print(str(trame["id"]) + " : " + str(masque) + "\n") #debug
        # création de la trame en focntion du masque
        # si on a pas de trame précédente mais trame de synchro (première trame a être reconstitué)
        if trame["prev"]== [] and trame["sync"] != []:
            #ajoute la partie data
            offset = 8-trame["dlc"]
            for index, octet in enumerate(trame["sync"]):
                if data_sorter[index + offset] == "1":
                    data = randint(0,255)
                else:
                    data = octet
                list_data.append(data)
            trame["prev"] = trame["sync"]
        
        # si on a une trame précédente
        else:
            #parcour la liste des datas précédente et récupère la valeur précédente
            for trame_prev in trame_prev_per_id:
                if trame_prev["id"] == trame["id"]:
                    trame["prev"] = trame_prev["trame_prev"]
                    break
            #ajoute la partie data
            offset = 8-trame["dlc"]
            for index, octet in enumerate(trame["prev"]):
                if data_sorter[index + offset] == "1":
                    data = randint(0,255)
                else:
                    data = octet
                list_data.append(data)

            
    
    # Mise en mémoire de la dernière trame pour chaque id    
    id_finded = False # Flag pour ajouter des trames a la strucutre si l'id n'a jamais été ajouté  
    for el in trame_prev_per_id:
        if el["id"] == trame["id"]:
            el["trame_prev"] = list_data
            id_finded = True
            break
    if id_finded == False:
        trame_prev_per_id.append({"id":trame["id"],"trame_prev":list_data})
    
    # maj compteur 
    #trame["cpt"] = (trame["cpt"] + 1)%10

    # return a struct
    return_struct = {'data_sorter': data_sorter, 'list_data':list_data, 'id':trame["id"], 
                     'dlc':trame["dlc"], 'sync':trame["sync"],'prev':trame["prev"] }
    return return_struct

# Save any struct as json file
def save_json(struct):
    # Récupération de la date et de l'heure actuelle pour le nom
    now = datetime.datetime.now()
    now_str = now.strftime("%d-%m-%Y_%H-%M-%S")
    # Get current directory
    current_dir = os.getcwd()
    # Set subdirectory
    sub_dir = "test"
    # Create the file name
    file_name =  os.path.join(current_dir,sub_dir,"compressed_" + now_str + ".json")
    # Enregistrez la structure dans un fichier texte au format JSON
    with open(file_name, 'w') as fichier:
        json.dump(struct, fichier, indent=1)#, sort_keys=True)

# ---------------------------MAIN-------------------------------------

# ----------------------Init MQTT--------------------------
ENDPOINT = "a1xvyu1lci6ieh-ats.iot.eu-west-3.amazonaws.com"
CLIENT_ID = "Publish_testAwsPy"
PATH_TO_CERTIFICATE = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-certificate.pem.crt"
PATH_TO_PRIVATE_KEY = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-private.pem.key"
PATH_TO_AMAZON_ROOT_CA_1 = "certificates/root.pem"
MESSAGE = "Coucou"
TOPIC = "pyAws"
SAVE_ACTIVATED = True #active ou désactive la sauvegarde des datas mqtt
SAVE_COUNT = 100 #Timer pour sauvegarde data mqtt  5000 = 1 min en debug

# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

# Create the client
mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=PATH_TO_CERTIFICATE,
            pri_key_filepath=PATH_TO_PRIVATE_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_AMAZON_ROOT_CA_1,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=6
            )
print("Connecting ⌚")
# Make the connect() call
connect_future = mqtt_connection.connect()
# Future.result() waits until a result is available
connect_future.result()
print("Connected ✅")

#------------------------Init DBC--------------------------
name_dbc =  "DBC_VCU_V2.dbc"
#handleur dbc
database = cantools.database.load_file(name_dbc)

#------------------------Init Algo--------------------------
#list 
list_10ms = []
list_100ms = []
list_1000ms = []
#dict
d_10ms = {}
d_100ms = {}
d_1000ms = {}
# Compteurs de trames
compteur_10ms = 0
# Var pour stocker les trames précédentes par id (global)
trame_prev_per_id = [{"id":None,"trame_prev":[]}] #Première valeure inutile, juste pour ne pas que la strcutrue soit vide
    

#decode le DBC 
#enregistre les id en fonction de la période des trames
for index,msg in enumerate(database.messages):
    id = msg.frame_id
    cycle = msg.cycle_time
    dlc = msg.length
    synchro = [] #trame de synchronisation
    previous = [] #trame précédente
    #cpt = 0 #compteur de trame par id
    if cycle == 100 :
        d_100ms = {"id": id , "dlc":dlc,"sync":synchro,"prev":previous}
        list_100ms.append(d_100ms)
    elif cycle == 1000 :
        d_1000ms = {"id": id , "dlc":dlc,"sync":synchro,"prev":previous}
        list_1000ms.append(d_1000ms)
    else:
    #cas le plus critique
        d_10ms = {"id": id ,"id_compressed":index, "dlc":dlc,"sync":synchro,"prev":previous}
        list_10ms.append(d_10ms)


# #Lance les threads
t_10ms = threading.Thread(target= send_mqtt_10ms)
t_10ms.start()
#t_100ms.start()
#t_1000ms.start()