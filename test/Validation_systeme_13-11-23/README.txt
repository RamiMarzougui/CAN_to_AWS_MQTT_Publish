# Softs utilisées
- Mqtt Publisher : mqtt_loader_compressed_V1-1
- Mqtt Subscriber : mqtt_reader_compressed_V1-0

# Conditions de test
- Envoi de 1700 trames à 10Hz sur AWS et re-lecture par interruption.
- Les 1700 trames sont composées de 17 trames d'id CAN différentes.
- Les deux fichiers résultants des deux soft sont traités, seulement la partie 
  data hexa brut est conservé et comparé.

# Résutat
Aucune différence entre les deux fichiers.
Fichiers dans le même orde.

# Bilan
Validation de l'algo de compression, de décompression et de AWS MQTT.