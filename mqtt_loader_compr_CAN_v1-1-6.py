from canlib import canlib, Frame
import can
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
from can_nwt import CanNwt 

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
        print("Saved ✅")

# Decode le DBC 
def read_dbc(): 
    dbc_readed = []
    #enregistre les id en fonction de la période des trames
    for index,msg in enumerate(database.messages):
        id = msg.frame_id
        cycle = msg.cycle_time
        dlc = msg.length
        if cycle == 10:
            priority = 3
        elif cycle == 100:
            priority = 2 
        else:
            priority = 1
        data_dbc = {"id": id ,"id_compressed":index, "dlc":dlc,
                    "cycle": cycle,"priority":priority}
        dbc_readed.append(data_dbc)
    return dbc_readed

# Compteur de temps 100ms
def timer_100ms():
    global start_tempo_100ms
    # RAZ flag
    res_100ms_flag = False
    # get current time ms 
    current_time_ms = time.time()*1000 #*1000 pour mettre en ms
    # for the first shot
    if start_tempo_100ms == 0:
        start_tempo_100ms = current_time_ms
    # Test si overflow
    if (current_time_ms-start_tempo_100ms) >=99:
        res_100ms_flag = True
    return res_100ms_flag

# Compteur de temps 500ms
def timer_500ms():
    global start_tempo_500ms
    # RAZ flag
    res_500ms_flag = False
    # get current time
    current_time_ms = time.time()*1000 #*1000 pour mettre en ms
    # for the first shot
    if start_tempo_500ms == 0:
        start_tempo_500ms = current_time_ms
    # Test si overflow
    if (current_time_ms-start_tempo_500ms) >=499:
        res_500ms_flag = True
    return res_500ms_flag

# Compteur de temps 1000ms
def timer_1000ms():
    global start_tempo_1000ms
    # RAZ flag
    res_1000ms_flag = False
    # get current time
    current_time_ms = time.time()*1000 #*1000 pour mettre en ms
    # for the first shot
    if start_tempo_1000ms == 0:
        start_tempo_1000ms = current_time_ms
    # Test si overflow
    if (current_time_ms-start_tempo_1000ms) >=999:
        res_1000ms_flag = True
    return res_1000ms_flag

# Compress la partie data des trames en focniton du data_sorter
def compress_with_sorter(sorter,data,dlc):
    # init
    data_compressed =[]
    # vrai data sorter (pas sous le format 8 bits)
    sorter_real = sorter[-dlc:]
    for index, octet in enumerate(sorter_real):
        if octet=="1":
            data_compressed.append(data[index])
    return data_compressed

# Compress la partie data et l'id du message CAN
def compress_can_msg(msg):
    # Init 
    sorter = ""  #Data_sorter
    
    # Get the compressed id
    for el in dbc_readed:
        if msg["id"]==el["id"]:
            msg["id_compressed"] = el["id_compressed"]

    # Flag pour savoir si des datas précédente exits pour l'id
    prev_data_exist = False

    # Check si des datas on déjà était lues pour cette id 
    # Si existe alors on compresse
    for i , prev_msg in enumerate(prev_msg_per_id):
        if msg["id"] == prev_msg["id"]:
            # Init prev values
            prev_cpt_syncro = prev_msg["cpt_sync"]
            prev_data =  prev_msg["data"]
            # Flag pour surveiller l'overflow du compteur)
            cpt_sync_overflow = False
            # Check si la trame a overflow son cpt_sync (elle a besoin d'une synchronisation)
            if prev_cpt_syncro>=9:
                for k in range (msg["dlc"]):
                    sorter += "1"
                # RAZ compteur de synchro
                cpt_sync_overflow = True
            else:
                # Création du data_sorter
                for j in range (msg["dlc"]):
                    if msg["data"][j]==prev_data[j]:
                        sorter += "0"
                    else:
                        sorter += "1"
            # Maj compteur de synchro
            if cpt_sync_overflow:
                msg["cpt_sync"] = 0
            else:
                msg["cpt_sync"] = prev_cpt_syncro +1
            #mise du data_sorter sur 8 bits (rajout zero a gauche si besoin)
            sorter = sorter.zfill(8)
            msg["sorter"] = sorter
            msg["prev_data_hex"] = [hex(entier) for entier in prev_data] # debug only

            # Mise en mémoire de l'état
            prev_msg_per_id[i] = msg
            # Maj flag car data trouvé
            prev_data_exist = True
            # Pour sortir du for 
            break
            
    # Si les datas n'existent pas 
    if prev_data_exist == False:
        #création du sorter
        for i in range (msg["dlc"]):
            sorter += "1"
         #mise du data_sorter sur 8 bits (rajout zero a gauche si besoin)
        sorter = sorter.zfill(8)
        msg["sorter"] = sorter
        prev_msg_per_id.append(msg)
    
    # Debug
    if len(sorter)>8:
        print("error size data sorter")

    # Compression par rapport au data sorter
    msg["data_compressed"] = compress_with_sorter(sorter,msg["data"],msg["dlc"])
    msg["data_compressed_hex"] = [hex(entier) for entier in  msg["data_compressed"]]
    # Créer les datas en hexa (pour le debug uniquement)
    msg["data_hex"] = str([hex(x) for x in  msg["data"]])
    pass
 
def get_priority():
    for el in dbc_readed:
        if can_msg["id"]==el["id"]:
            can_msg["priority"] = el["priority"]
            can_msg["debug"] = str(el["priority"]) + " : " + str(can_msg["time"]) # debug only
            break

# Convertit les msg pour MQTT
def convert_to_mqtt(concatened_msg):
    global cpt_frame_prio1
    global cpt_frame_prio2
    global cpt_frame_prio3
    
    # Init/RAZ msg_mqtt
    msg_mqtt = ""
    new_frame_2concat = ""
    # ------- Créer le Header de la trame ------------
    # Nombre de trames
    nb_trames = len(concatened_msg)
    # Timestamp, on prend le premier msg can comme réf
    time_s = int(str(concatened_msg[0]["time"])[:-3]) # Garde que les secs
    
    # Update du compteur du header en fonction de la priorité
    packet_prio = concatened_msg[0]["priority"]
    cpt_frame = None
    if packet_prio == 1:
        cpt_frame_prio1 = (cpt_frame_prio1+1)%256 #1s
        cpt_frame = cpt_frame_prio1
    elif packet_prio == 2:
        cpt_frame_prio2 = (cpt_frame_prio2+1)%256 #500ms
        cpt_frame = cpt_frame_prio2
    elif packet_prio == 3:
        cpt_frame_prio3 = (cpt_frame_prio3+1)%256 #100ms
        cpt_frame = cpt_frame_prio3
    
    # Concaténation du topic header
    header = nb_trames.to_bytes(1,'big') + time_s.to_bytes(4,'big') + cpt_frame.to_bytes(1,'big')
    # Ajout de l'header à la trame finale
    msg_mqtt = header   

    #debug only
    msg_mqtt_not_convert =[]

    # ------- Créer la partie frame ------------
    for msg_cctn in concatened_msg:
        # id
        id_compressed = msg_cctn["id_compressed"]
        # ms_ts
        ms_ts = int(str(msg_cctn["time"])[-3:]) #garde que la partie ms
        #debug_history.append(time_s*1000 + ms_ts)
        
        #test_with_history.append({"sec":time_s,"ms":ms_ts,"API":msg_cctn["time"]})
        # sorter
        sorter = msg_cctn["sorter"]
        # Convert the data sorter
        sorter_bin = ''.join(map(str, sorter))  # Converti la liste binaire en une chaîne binaire
        sorter_int = int(sorter_bin, 2) # Converti en décimal
        # Partie Data
        data = bytes(msg_cctn["data_compressed"])
        new_frame_2concat = id_compressed.to_bytes(1,'big') + ms_ts.to_bytes(2,'big')+ sorter_int.to_bytes(1,'big') + data
        msg_mqtt += new_frame_2concat
        # Debug only
        msg_mqtt_not_convert.append({"id" :id_compressed, "ms" :ms_ts, "sorter":sorter, "data" :msg_cctn["data_compressed"]})
    # retour 
    return msg_mqtt

#Check, concatène et envoi les trames à 100ms
def concat_and_send_100ms():
    global msg_concatened_100ms
    global msg_mqtt_history
    global concatened_msg_history
    global start_tempo_100ms
    global cpt_rank
    global prev_time_100ms
    global debug_prev
    global debug_history
    
    # test si time elapsed
    time_as_elapsed = timer_100ms()

    debug_detect = False
    prev_absolu = 0
    now_absolu = 0
    time_difference = 0

    # test si nouvelle seconde
    if prev_time_100ms !=0:
        prev_absolu = int(prev_time_100ms/1000)
        now_absolu = int(can_msg["time"]/1000)
        time_difference =  now_absolu - prev_absolu
        if time_difference >= 1:
            debug_detect = True
            time_as_elapsed = True

    # Maj prev time
    prev_time_100ms = can_msg["time"]

    # Debug
    # debug_history.append({"prev":prev_absolu,
    #                       "now":now_absolu,
    #                       "diff":time_difference,
    #                       "detected":debug_detect,
    #                       "elapsed":time_as_elapsed})
    
    if not time_as_elapsed:
        # Flag pour savoir si un ID a déjà était ajouté aux trames concats
        id_already_exist = False
        # Check si trame existe déja
        for i,msg in enumerate(msg_concatened_100ms):
            # Si l'id est déjà ajouté alors on maj les données associés
            if  can_msg["id"] == msg["id"]:
                # Si existe, maj trame avec la nouvelle
                msg_concatened_100ms[i] = can_msg
                # Maj Flag
                id_already_exist = True
                break
        if id_already_exist == False:
            #Ajout trame a concat
            msg_concatened_100ms.append(can_msg)
            
    # Append à la liste 100ms
    elif time_as_elapsed and msg_concatened_100ms: #Timeout détecté
        #debug_history.append(len (msg_concatened_100ms))
        #debug_prev = msg_concatened_100ms[0]['time'] # debug
        #debug_history.append(msg_concatened_100ms)
        # Ajout rank pour le debug only
        # for el in msg_concatened_100ms:
        #     el["rank"] = cpt_rank
        # cpt_rank += 1
        # Compresse trame par trame
        for i,msg in enumerate(msg_concatened_100ms):
            # Compression
            compress_can_msg(msg_concatened_100ms[i])
        # Conversion
        msg_mqtt = convert_to_mqtt(msg_concatened_100ms)
        # Envoi MQTT
        mqtt_connection.publish(topic=TOPIC, payload= msg_mqtt, qos=mqtt.QoS.AT_LEAST_ONCE)
        # Ajout historique (DEBUG)
        msg_mqtt_history.append(str(msg_mqtt))
        concatened_msg_history.append(msg_concatened_100ms)
        # RAZ trame concaténée
        # msg_concatened_100ms = []
        # Flag pour savoir si un ID a déjà était ajouté aux trames concats
        id_already_exist2 = False
        for i,msg in enumerate(msg_concatened_100ms):
            # Si l'id est déjà ajouté alors on maj les données associés
            if  can_msg["id"] == msg["id"]:
                # Si existe, maj trame avec la nouvelle
                msg_concatened_100ms[i] = can_msg
                # Maj Flag
                id_already_exist2 = True
                break
        if id_already_exist2 == False:
            #Ajout trame a concat
            msg_concatened_100ms.append(can_msg)
        # Maj Start tempo uniquement si la maj a été déctecté
        start_tempo_100ms = time.time()*1000


#Check, concatène et envoi les trames à 500ms
def concat_and_send_500ms():
    global msg_concatened_500ms
    global msg_mqtt_history
    global concatened_msg_history
    global start_tempo_500ms
    global prev_time_500ms

    # test si time elapsed
    time_as_elapsed = timer_500ms()

    # init
    prev_absolu = 0
    now_absolu = 0
    time_difference = 0

    # test si nouvelle seconde
    if prev_time_500ms !=0:
        prev_absolu = int(prev_time_500ms/1000)
        now_absolu = int(can_msg["time"]/1000)
        time_difference =  now_absolu - prev_absolu
        if time_difference >= 1:
            time_as_elapsed = True

    # Maj prev time
    prev_time_500ms = can_msg["time"]
	
    if not time_as_elapsed:
        # Flag pour savoir si un ID a déjà était ajouté aux trames concats
        id_already_exist = False
        # Check si trame existe déja
        for i,msg in enumerate(msg_concatened_500ms):
            # Si l'id est déjà ajouté alors on maj les données associés
            if  can_msg["id"] == msg["id"]:
                # Si existe, maj trame avec la nouvelle
                msg_concatened_500ms[i] = can_msg
                # Maj Flag
                id_already_exist = True
                break
        if id_already_exist == False:
            #Ajout trame a concat
            msg_concatened_500ms.append(can_msg)
            
    # Append à la liste 500ms
    elif time_as_elapsed and msg_concatened_500ms: #Timeout détecté
        for i,msg in enumerate(msg_concatened_500ms):
            # Compression
            compress_can_msg(msg_concatened_500ms[i])
        # Conversion
        msg_mqtt = convert_to_mqtt(msg_concatened_500ms)
        # Envoi MQTT
        mqtt_connection.publish(topic=TOPIC, payload= msg_mqtt, qos=mqtt.QoS.AT_LEAST_ONCE)
        # Ajout historique (DEBUG)
        msg_mqtt_history.append(str(msg_mqtt))
        concatened_msg_history.append(msg_concatened_500ms)
        # RAZ trame concaténée
        msg_concatened_500ms = []
        #Ajout trame a concat
        msg_concatened_500ms.append(can_msg)
        # Maj Start tempo uniquement si la maj a été déctecté
        start_tempo_500ms = time.time()*1000


#Check, concatène et envoi les trames à 1000ms
def concat_and_send_1000ms():
    global msg_concatened_1000ms
    global msg_mqtt_history
    global concatened_msg_history
    global start_tempo_1000ms
    global prev_time_1000ms

    # test si time elapsed
    time_as_elapsed = timer_1000ms()

    # init
    prev_absolu = 0
    now_absolu = 0
    time_difference = 0

    # test si nouvelle seconde
    if prev_time_1000ms !=0:
        prev_absolu = int(prev_time_1000ms/1000)
        now_absolu = int(can_msg["time"]/1000)
        time_difference =  now_absolu - prev_absolu
        if time_difference >= 1:
            time_as_elapsed = True

    # Maj prev time
    prev_time_1000ms = can_msg["time"]
	
    if not time_as_elapsed:
        # Flag pour savoir si un ID a déjà était ajouté aux trames concats
        id_already_exist = False
        # Check si trame existe déja
        for i,msg in enumerate(msg_concatened_1000ms):
            # Si l'id est déjà ajouté alors on maj les données associés
            if  can_msg["id"] == msg["id"]:
                # Si existe, maj trame avec la nouvelle
                msg_concatened_1000ms[i] = can_msg
                # Maj Flag
                id_already_exist = True
                break
        if id_already_exist == False:
            #Ajout trame a concat
            msg_concatened_1000ms.append(can_msg)
            
    # Append à la liste 1000ms
    elif time_as_elapsed and msg_concatened_1000ms: #Timeout détecté
        for i,msg in enumerate(msg_concatened_1000ms):
            # Compression
            compress_can_msg(msg_concatened_1000ms[i])
        # Conversion
        msg_mqtt = convert_to_mqtt(msg_concatened_1000ms)
        # Envoi MQTT
        mqtt_connection.publish(topic=TOPIC, payload= msg_mqtt, qos=mqtt.QoS.AT_LEAST_ONCE)
        # Ajout historique (DEBUG)
        msg_mqtt_history.append(str(msg_mqtt))
        concatened_msg_history.append(msg_concatened_1000ms)
        # RAZ trame concaténée
        msg_concatened_1000ms = []
        #Ajout trame a concat
        msg_concatened_1000ms.append(can_msg)
        # Maj Start tempo uniquement si la maj a été déctecté
        start_tempo_1000ms = time.time()*1000


# ---------------------------MAIN-------------------------------------

# ----------------------Init MQTT--------------------------
ENDPOINT = "a1xvyu1lci6ieh-ats.iot.eu-west-3.amazonaws.com"
CLIENT_ID = "Publish_testAwsPy"
PATH_TO_CERTIFICATE = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-certificate.pem.crt"
PATH_TO_PRIVATE_KEY = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-private.pem.key"
PATH_TO_AMAZON_ROOT_CA_1 = "certificates/root.pem"
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

# Valeur max de msg can que l'on peut conaténer dans une trame mqtt
MAX_CONCAT = 15
# Liste de structure sur les trames dans le dbc
dbc_readed = []
# msg lue sur le can
can_msg = []
# msg lue historique (debug only)
global can_msg_history
global msg_mqtt_history
global payload_history
global debug_history
global debug_prev
debug_prev = 0
debug_history = []
can_msg_history = []
msg_mqtt_history =[]
# message converti
converted_msg = []
# trame concatné à envoyer
concatened_msg =[]
# Previous msg per id, fausse premirèe data pour pouvoir boucler quand vide
prev_msg_per_id=[{"id":None,"cpt_sync":0}]
# Trame mqtt a envoyé
trame_mqtt =""
#init point display
point_display = 0
# Trame concat par prio
global prev_time_100ms
global prev_time_500ms
global prev_time_1000ms
global msg_concatened_100ms
global msg_concatened_500ms
global msg_concatened_1000ms
prev_time_100ms = 0
prev_time_500ms = 0
prev_time_1000ms = 0
msg_concatened_100ms =[]
msg_concatened_500ms =[]
msg_concatened_1000ms =[]
# Compteurs de trames
global cpt_frame_prio1
global cpt_frame_prio2
global cpt_frame_prio3
cpt_frame_prio1 = 0
cpt_frame_prio2 = 0
cpt_frame_prio3 = 0
# Var pour stocker les trames précédentes par id (global)
trame_prev_per_id = [{"id":None,"trame_prev":[]}] #Première valeure inutile, juste pour ne pas que la strcutrue soit vide
#debug
global cpt_rank
cpt_rank = 0

# Tempo pour les prioritées
global start_tempo_100ms
global start_tempo_500ms
global start_tempo_1000ms
start_tempo_100ms = 0
start_tempo_500ms = 0
start_tempo_1000ms = 0

#---------------------- Main --------------------------

#Lis le DBC
dbc_readed = read_dbc()

# create the CAN handler
h_can = CanNwt()
test_with_history =[]
#epoch time du dernier msg reçu 
last_msg_time = 9000000000
# Historique des trames concaténées (debug only)
#global concatened_msg_history
concatened_msg_history =[]

save_file = False
#Boucle infini
while True:
    # Save Json (debug only)
    if save_file == True:
        #save_json(msg_mqtt_history)
        #tab_debug = [element for sous_tableau in concatened_msg_history for element in sous_tableau]
        save_json(concatened_msg_history)
        save_file = False
        #break
    try:
        # Lis le message CAN 
        can_msg = h_can.ReadMessage()
        
                
        # Check si une trame a été lue
        if can_msg != "Error":
            #Récupère la priorité du message CAN
            get_priority()
            # maj l'epoch time de la denière trame reçue
            #last_msg_time = int(time.time())
            # Fait varier le publish
            point_display = (point_display+1)%10
            print("CAN msg received" + point_display*".")
            
            # Compress la partie data et l'id de la trame
            # compress_can_msg(can_msg)
            # Historique pour le debug
            can_msg_history.append(can_msg)
            #Check et concatène les trames à 100ms
            if can_msg["priority"] == 3:
                concat_and_send_100ms()
            if can_msg["priority"] == 2:
                concat_and_send_500ms()
            if can_msg["priority"] == 1:
                concat_and_send_1000ms()

            #Maj le reset des tempos
            
    except Exception as e:
        print (e)
        raise # Montre où est l'erreur

    pass
    #break