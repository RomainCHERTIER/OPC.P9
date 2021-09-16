#############################################################
# MIT License

# Copyright (c) 2021 Romain CHERTIER
# opensource.org/licenses/mit-license.php

###############################################################################

#
#                    Save WP
#
# Sauvegarde WordPress vers FTP
#
#
# @author Romain CHERTIER<romain.chertier@sfr.fr>
# @version 1.1
# @date 2021-08-09
#

from datetime import datetime, timedelta
import os
import shutil
import tarfile
import os.path
from ftplib import FTP
import configparser
import subprocess

################################   Constants   ################################

configPath = 'conf.ini'
now = datetime.now()
dateYYYYMMDD = now.strftime("%Y%m%d")


################################   Functions   ################################

#
# InitConfig
#
# Initialisation du fichier de configuration
#
#
def InitConfig():
    global config, configPath
    config = configparser.ConfigParser()
    config.read(configPath)
    config.sections()



#
# log
#
# Trace une information de Log
# @param string level niveau de la trace (ERROR ,WARNING, INFO)
# @param string msg message à tracer
#
def log(level, msg):
    global config
    logSection = config['Log']
    logDir = logSection['logDir']
    logFile = logSection['logFile']
    logFileExt = logSection['logFileExt']
    now = datetime.now()
    line = now.strftime("%Y%m%d %H%M%S") + " [" + level + "] " + msg
    print(line)
    dateYYYYMMDD = now.strftime("%Y%m%d")
    logAbsPath = logDir + logFile + dateYYYYMMDD + logFileExt
    try:
        fd = open(logAbsPath, "a")
        fd.write(line + "\n")
        fd.close()
    except Exception as err:
        print(" Erreur : " + format(err) + "\n")

#
#  logExit
#
# Trace une information de Log, puis stope le script avec un code retour
# @param string level niveau de la trace (ERROR ,WARNING, INFO)
# @param string msg message à tracer
#
def logExit(level, msg):
    log(level, msg)
    if (level == "ERROR"):
        exit(2)
    elif (level == "WARNING"):
        exit(1)
    else:
        exit(0)

#
# CreateWorkingDir
#
# Création du dossier de travail
#
#
#
def CreateWorkingDir():
    WDSection = config['WD']
    rep = WDSection['workingDir']
    try:
        if os.path.exists(rep) :
            logExit('ERROR', 'répertoire de travail existant')
        else :
            os.mkdir(rep)
            log('INFO', 'répertoire de travail créé')
    except Exception as ose:
        logExit('ERROR', "CreateWorkingDir : %s" % (ose))

#
# DeleteWorkingDir
#
# Suppression du dossier de travail
#
#
#
def DeleteWorkingDir():
    WDSection = config['WD']
    rep = WDSection['workingDir']
    try :
        shutil.rmtree(rep, ignore_errors=True)
        log('INFO', 'répertoire de travail supprimé')
    except Exception as ose:
        logExit('ERROR', "deleteWorkingDir : %s" % (ose))

#
# CreateRep
#
# Création du répertoire de stockage des fichiers à sauvegarder
#
#
#
def CreateRep():
    global dateYYYYMMDD
    WDSection = config['WD']
    rep = WDSection['workingDir'] + WDSection['archiveDir']
    try:
        os.mkdir(rep)
        log('INFO', 'Dossier créé')
        return rep
    except Exception as ose:
        logExit('ERROR', "CreateRep : %s" % (ose))

#
# CpFichier
#
# Copie l'ensemble des fichiers nécessaire au fonctionnement du Wordpress vers le répertoire de stockage
# @param string archiveDir chemin absolu vers le repertoire de stockage 
#
#
def CpFichier(archiveDir):
    global config
    CpSection = config['Cp']
    src = CpSection['source']
    des = archiveDir
    cp = CpSection['cp']
    copie = [cp,'-r',src,des]
    try:
        res = subprocess.Popen(copie, stdout=subprocess.PIPE)
        res.wait()
        if res.returncode != 0:
            logExit('ERROR', "os.wait:exit status != 0 :%s\n" % (res.returncode))
        else:
            log('INFO', "os.wait:({},{})".format(res.pid, res.returncode))
    except OSError as ose:
        logExit('ERROR', "Copie : %s" % (ose))

#
# DumpSql
#
# Création du Dump SQl
# @param string archiveDir chemin absolu vers le repertoire de stockage 
#
#
def DumpSql(archiveDir):
    global dateYYYYMMDD, config
    DumpSection = config['Dump']
    user = DumpSection['user']
    password = DumpSection['password']
    host = DumpSection['host']
    database = DumpSection['database']
    mysqldump = DumpSection['mysqldump']
    archiveFile = archiveDir + "%s.gz" % (database + "_" + dateYYYYMMDD)
    args = mysqldump+" -u "+user+ " -p"+password+ " -h "+host+ " -c -e --opt --add-drop-database --databases " +database+" | gzip -c > "+archiveFile
    try:
        res = subprocess.Popen(args, stdin=subprocess.PIPE, shell=True)
        res.wait()
        if res.returncode != 0:
            logExit('ERROR', "os.wait:exit status != 0 :%s\n" % (res.returncode))
        else:
            log('INFO', "os.wait:({},{})".format(res.pid, res.returncode))
    except OSError as ose:
        logExit('ERROR', "popen : %s" % (ose))

#
# CreateTarFile
#
# Compression du répertoire de stockage avant envoi FTP
# @param string archiveDir chemin absolu vers le repertoire de stockage 
# @return string nom du fichier compressé
#
def CreateTarFile(archiveDir):
    global config, dateYYYYMMDD
    TarfileSection = config['Tarfile']
    WDSection = config['WD']
    filename = WDSection['workingDir'] + (TarfileSection['output_filename'] + dateYYYYMMDD+'.tar')
    repertoire = WDSection['workingDir'] + WDSection['archiveDir']
    source_dir = archiveDir
    try:
        with tarfile.open(filename, "x:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
        log('INFO', 'Compression effectuée : '+filename)
        shutil.rmtree(repertoire, ignore_errors=True)
        return filename
    except OSError as ose:
        logExit('ERROR', "Tarfile : %s" % (ose))

#
# CpFTP
#
# Copie du fichier compressé vers le serveur FTP
# @param string archive chemin absolu vers fichier compressé
#
#
def CpFTP(archive):
    global config
    CpFTPSection = config['FTP']
    WDSection = config['WD']
    server = CpFTPSection['server']
    port = int(CpFTPSection['port'])
    user = CpFTPSection['user']
    passwd = CpFTPSection['passwd']
    destination = CpFTPSection['destination']
    dirWork = WDSection['workingDir']
    try:
        ftp = FTP()
        ftp.connect(server,port)
        ftp.sendcmd("USER " + user)
        ftp.sendcmd("PASS " + passwd)
        ftp.cwd(destination)
        dirFTP = dirWork
        toFTP = os.listdir(dirFTP)
        for archive in toFTP:
            with open(os.path.join(dirFTP, archive), 'rb') as file:
                ftp.storbinary(f'STOR {archive}', file)
        ftp.quit()
        print("sent file: " + archive)
        log('Info', 'transfert effectué')
    except OSError as ose:
        logExit('ERROR', "CpFTP : %s" % (ose))

#
# ASupprimer
#
# Indique si la date du fichier est posterieure au nombre de jours de rétention (vrai le fichier est a supprimé, faux il doit etre conservé)
# @param string dateFichier date du fichier au format AAAAMMJJ
# @return boolean vrai si anterieur faux si posterieur
#
def ASupprimer(dateFichier):
    global now, config
    DateSection = config['Date']
    nbJours = int(DateSection['NbJours'])
    dateLimite = now - timedelta(days=nbJours)
    dateLimite = int(dateLimite.strftime("%Y%m%d"))
    if dateLimite < int(dateFichier) :
        return False
    else :
        return True

#
# FTP
#
# Gestion des sauvegardes presentes sur le serveur FTP nettoyage des fichiers trop anciens
#
#
#
def FTp():
    global config
    CpFTPSection = config['FTP']
    server = CpFTPSection['server']
    port = int(CpFTPSection['port'])
    user = CpFTPSection['user']
    passwd = CpFTPSection['passwd']
    destination = CpFTPSection['destination']
    try:
        ftp = FTP()
        ftp.connect(server, port)
        ftp.sendcmd("USER " + user)
        ftp.sendcmd("PASS " + passwd)
        ftp.cwd(destination)
        data = []
        ftp.dir(data.append)
        ftp.quit()
        for line in data:
            aLine=line.split()
            fichier = aLine[8]
            prefixFichier = fichier[:6]
            if prefixFichier == "backup":
                 dateFichier = int(fichier[6:14])
                 if ASupprimer(dateFichier) :
                      log("INFO", "sauvegarde a supprimer : "+ fichier)
                      ftp.connect(server, port)
                      ftp.sendcmd("USER " + user)
                      ftp.sendcmd("PASS " + passwd)
                      ftp.cwd(destination)
                      ftp.delete(fichier)
                      log ("INFO", " Fichier : "+fichier+" supprimé")
                      ftp.quit()
    except Exception as ose:
        log('ERROR', "FTP : %s" % (ose))

##################################   Main   ###################################
#
# appel des fonctions
#
InitConfig()
try:
    CreateWorkingDir()
    archiveDir = CreateRep()
    CpFichier(archiveDir)
    DumpSql(archiveDir)
    archive = CreateTarFile(archiveDir)
    CpFTP(archive)
    FTp()
    DeleteWorkingDir()
    logExit('INFO', 'Fin du script correcte')
except Exception as e:
    log("ERROR", e)

