from canlib import canlib, Frame
import time
import random
from random import randint
import cantools
import threading

#Send Id avec un cycle de 10ms
def send_can_10ms():
    while True:
        try: 
            #init
            can_msg = None

            #parcour les trames de la liste
            for indexe,el in enumerate(list_10ms):
                #init
                list_data = []
                
                #récupère les datas
                list_data = create_data(el)

                #préparation des trames a envoyer
                if el["id"] == 452664324 or el["id"] == 452664320:
                    can_msg  = Frame(id_=el["id"], data=list_data, dlc = el["dlc"], flags=canlib.canMSG_EXT)
                else:
                    can_msg  = Frame(id_=el["id"], data=list_data, dlc = el["dlc"], flags=canlib.MessageFlag.STD )

                #envoi des trames
                ch_a.write(can_msg)
        except Exception as e:
            print (e)
        time.sleep(0.01)

#Send Id avec un cycle de 100ms
def send_can_100ms():
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
                ch_a.write(can_msg)
        except Exception as e:
            print (e)
        time.sleep(0.1)

#Send Id avec un cycle de 1000ms
def send_can_1000ms():
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
                ch_a.write(can_msg)
        except Exception as e:
            print (e)
        time.sleep(1)

def create_data(trame):
    list_data = []
    #parcour les trames de la liste
    #génère data aléatoire pour chaque trame si sync est à 0 ou si index multiple de 10
    if trame["sync"] == [] or trame["cpt"] == 0:
        for octet in range (0,trame["dlc"]):
            list_data.append(randint(0,255))
        trame["sync"] = list_data
        trame["prev"] = []
    #sinon 
    else :
        #init masque
        masque = []
        #création du masque
        masque = [random.choice([0, 1]) for bit in range(trame["dlc"])]
        print(str(trame["id"]) + " : " + str(masque) + "\n") #debug
        #création de la trame en focntion du masque
        
        #si on a pas de trame précédente mais trame de synchro (première trame a être reconstitué)
        if trame["prev"]== [] and trame["sync"] != []:
            for place, octet in enumerate(trame["sync"]):
                if masque[place] == 1:
                    data = randint(0,255)
                else:
                    data = octet
                list_data.append(data)
            trame["prev"] = list_data
        
        #si on a une trame précédente
        else:
            for place, octet in enumerate(trame["prev"]):
                if masque[place] == 1:
                    data = randint(0,255)
                else:
                    data = octet
                list_data.append(data)
            trame["prev"] = list_data
    
    #maj compteur 
    trame["cpt"] = (trame["cpt"] + 1)%10

    #debug 
    # if trame["cpt"] == 9:
    #     print("debug")

    #return
    return list_data

#MAIN
#init
name_dbc =  "DBC_VCU_V2.dbc"
#Open a virtual channel
ch_a = canlib.openChannel(channel=0,flags=canlib.Open.ACCEPT_VIRTUAL) 
# use setBusParams() to set the canBitrate to 1M.
ch_a.setBusParams(canlib.canBITRATE_1M)
# Channel ready to receive and send messages.
ch_a.busOn()
#handleur dbc
database = cantools.database.load_file(name_dbc)
#list 
list_10ms = []
list_100ms = []
list_1000ms = []
#dict
d_10ms = {}
d_100ms = {}
d_1000ms = {}

#decode le DBC 
#enregistre les id en fonction de la préiode des trames
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
        #cas le moins critique
        #list_1000ms.append(id)


# #Lance les threads
t_10ms = threading.Thread(target= send_can_10ms)
t_100ms = threading.Thread(target= send_can_100ms)
t_1000ms = threading.Thread(target= send_can_1000ms)
t_10ms.start()
t_100ms.start()
t_1000ms.start()