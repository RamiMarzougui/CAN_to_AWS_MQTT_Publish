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

global compteur_10ms


#Send Id avec un cycle de 10ms
def send_mqtt_10ms():
    global compteur_10ms
    # Backup communication mqtt
    mqtt_backup = []
    # msg a publier sur mqtt
    msg_publish = []
    # timer pour backup
    timer = 0
    while True:
        try: 
            # init
            can_msg = None
            trame = ""
            ms_ts = 0
            # Backup des valeurs calculées pour les trames
            trame_backup = []  
            
            # ------- Créer le Header de la trame ------------
            # Nombre de trames
            nb_trames = format(len(list_10ms),"02X")
            # Timestamp
            epoch_s = format(int(t.time()),"08X")
            # Compteur
            compteur_10ms += 1
            # Concaténation du topic header
            header = nb_trames + epoch_s + format(compteur_10ms,"02X")


            # ------ Créer la partie variable de la Trame ----
            #parcour les trames de la liste
            for index,el in enumerate(list_10ms):
                #init
                list_data = []
                data_sorter = []
            
                #récupère les datas
                created_trame = create_data(el)  #Récupère la strcuture de la trame compressé généré alétoirement
                list_data = created_trame['list_data'] #uniquement les données de la trame
                data_sorter = created_trame['data_sorter'] #récup le data_sorter

                #préparation des trames a envoyer
                # Create the id 
                id_compressed  = format(index,'02X')

                # Create the ms timestamp
                ms_ts += random.randint(0,20)

                # Convert the data sorter
                data_sorter_bin = ''.join(map(str, data_sorter))  # Converti la liste binaire en une chaîne binaire
                data_sorter_int = int(data_sorter_bin, 2) # Converti en décimla
                data_sorter_hex = format(data_sorter_int,"02X")

                #Convert the data part
                data_hex = ''.join([format(nombre, '02X') for nombre in list_data])

                # Fabrique la trame concaténé
                new_concatened_trame = id_compressed + format(ms_ts,'04X') + data_sorter_hex + data_hex
                trame  += new_concatened_trame #concatène les trames
                
                # Fabrique le back up de la trame
                trame_backup.append({'id': created_trame['id'],'dlc': created_trame['dlc'],
                                     'sync': created_trame['sync'],'prev': created_trame['prev'],
                                     'data': created_trame['list_data'],'id_compressed':id_compressed,
                                     'data_sorter_bin':data_sorter_bin, 'data_sorter_hex':data_sorter_hex,
                                     'data_compressed':data_hex, 'trame_sended':new_concatened_trame })
            
            # -----------------Fabrique la trame finale a envoyer--------------
            msg_mqtt = header+trame
            # envoi des trames
            mqtt_connection.publish(topic=TOPIC, payload= msg_mqtt, qos=mqtt.QoS.AT_LEAST_ONCE)
            # fabrique le backup de la com mqtt
            mqtt_backup.append({'header':header, 'trame':trame,
                                'msg_mqtt':msg_mqtt, 'trame_backup':trame_backup})
            print("Published ✅")
        except Exception as e:
            print (e)
            print("Not published ❌")
        time.sleep(0.01)
        #--------------Gestion timer et sauvegarde si besoin --------------------------
        timer +=1
        if timer >= SAVE_TIMER and SAVE_ACTIVATED: #save toutes les min si sauveagrde activée
            try:
                # Récupération de la date et de l'heure actuelle pour le nom
                now = datetime.datetime.now()
                now_str = now.strftime("%d-%m-%Y_%H-%M-%S")
                file_name = now_str + ".json"
                # Enregistrez la structure dans un fichier texte au format JSON
                with open(file_name, 'w') as fichier:
                    json.dump(mqtt_backup, fichier, indent=4, sort_keys=True)
                print("Saved ✅")
            except:
                print("Not saved ❌")

#Send Id avec un cycle de 100ms
def send_mqtt_100ms():
    while True:
        try:
            #init
            can_msg = None

            #génère data aléatoire pour chaque trame
            for el in list_100ms:
                #init
                list_data = []
                
                #récupère les datas
                list_data = create_data(el)

                can_msg  = Frame(id_=el["id"], data=list_data, dlc = el["dlc"], flags=canlib.MessageFlag.STD )
                # ch_a.write(can_msg)
        except Exception as e:
            print (e)
        time.sleep(0.1)

#Send Id avec un cycle de 1000ms
def send_mqtt_1000ms():
    #mémoire pour debug
    memory_tab = [] #mémoire pour debug 
    while True:
        try:
            #init
            can_msg = None

            #génère data aléatoire pour chaque trame
            for el in list_1000ms:
                #init
                list_data = []
                #récupère les datas
                list_data = create_data(el)
               
                #debug
                #memory_tab.append(el)
                can_msg  = Frame(id_= el["id"], data=list_data, dlc = el["dlc"], flags=canlib.MessageFlag.STD )
                # ch_a.write(can_msg)
        except Exception as e:
            print (e)
        time.sleep(1)

def create_data(trame):
    list_data = []
    return_struct =[]
    # init data_sorter
    data_sorter = []
    #parcour les trames de la liste
    #génère data aléatoire pour chaque trame si sync vide ou si cpt =0
    if trame["sync"] == [] or trame["cpt"] == 0:
        for octet in range (0,trame["dlc"]): 
            list_data.append(randint(0,255)) #génération trame
        trame["sync"] = list_data # la trame deviens alors la trame de synchro
        trame["prev"]= [] #trame prev est vide car elle nexiste pas et/ou plus
        data_sorter = [1,1,1,1,1,1,1,1] #car toutes les datas sont nouvelles
    #sinon 
    else :
        # création du masque
        data_sorter = [random.choice([0, 1]) for bit in range(trame["dlc"])]
        # print(str(trame["id"]) + " : " + str(masque) + "\n") #debug
        # création de la trame en focntion du masque
        # si on a pas de trame précédente mais trame de synchro (première trame a être reconstitué)
        if trame["prev"]== [] and trame["sync"] != []:
            for place, octet in enumerate(trame["sync"]):
                if data_sorter[place] == 1:
                    data = randint(0,255)
                else:
                    data = octet
                list_data.append(data)
            trame["prev"] = list_data
        
        # si on a une trame précédente
        else:
            for place, octet in enumerate(trame["prev"]):
                if data_sorter[place] == 1:
                    data = randint(0,255)
                else:
                    data = octet
                list_data.append(data)
            trame["prev"] = list_data
    
    # maj compteur 
    trame["cpt"] = (trame["cpt"] + 1)%10

    # debug 
    # if trame["cpt"] == 9:
    #     print("debug")

    # return a struct
    return_struct = {'data_sorter': data_sorter, 'list_data':list_data, 'id':trame["id"], 
                     'dlc':trame["dlc"], 'sync':trame["sync"],'prev':trame["prev"] }
    return return_struct

# ---------------------------MAIN-------------------------------------

# ----------------------Init MQTT--------------------------
ENDPOINT = "a1xvyu1lci6ieh-ats.iot.eu-west-3.amazonaws.com"
CLIENT_ID = "testAwsPy"
PATH_TO_CERTIFICATE = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-certificate.pem.crt"
PATH_TO_PRIVATE_KEY = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-private.pem.key"
PATH_TO_AMAZON_ROOT_CA_1 = "certificates/root.pem"
MESSAGE = "Coucou"
TOPIC = "pyAws"
SAVE_ACTIVATED = False #active ou désactive la sauvegarde des datas mqtt
SAVE_TIMER = 10 #Timer pour sauvegarde data mqtt  6000 = 1 min

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

#decode le DBC 
#enregistre les id en fonction de la période des trames
for msg in database.messages:
    id = msg.frame_id
    cycle = msg.cycle_time
    dlc = msg.length
    synchro = [] #trame de synchronisation
    previous = [] #trame précédente
    cpt = 0 #compteur de trame par id
    if cycle == 100 :
        d_100ms = {"id": id , "dlc":dlc,"sync":synchro,"prev":previous,"cpt":cpt}
        list_100ms.append(d_100ms)
    elif cycle == 1000 :
        d_1000ms = {"id": id , "dlc":dlc,"sync":synchro,"prev":previous,"cpt":cpt}
        list_1000ms.append(d_1000ms)
    else:
        #cas le plus critique
        d_10ms = {"id": id , "dlc":dlc,"sync":synchro,"prev":previous,"cpt":cpt}
        list_10ms.append(d_10ms)


# #Lance les threads
t_10ms = threading.Thread(target= send_mqtt_10ms)
t_100ms = threading.Thread(target= send_mqtt_100ms)
t_1000ms = threading.Thread(target= send_mqtt_1000ms)
t_10ms.start()
#t_100ms.start()
#t_1000ms.start()