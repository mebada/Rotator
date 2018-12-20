#!/usr/bin/python
import shutil
import sys
#import argparse
import logging
import logging.handlers
import os
from xml.dom.minidom import parse
import xml.dom.minidom
from datetime import datetime
import time
import fnmatch
import gzip
import ntpath



def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

 

def getFilteredFiles(directory,pattern,expireAgeInMin,maxCount,maxSizeInK,logger):
    _filteredfiles=set()
    _now = time.mktime(datetime.now().timetuple())
    files = sorted(os.listdir(directory),key= lambda p:os.path.getctime(os.path.join(directory,p)))
    for _f in files:
       if expireAgeInMin== -1:
          break
       if fnmatch.fnmatch(_f,pattern):
          _f_time = os.path.getmtime(directory+'/'+_f) #get file creation/modification time
          diff =  _now - _f_time
          logger.debug(str(diff)+" "+ _f)
          if diff > 60 * int(expireAgeInMin):
              _filteredfiles.add(os.path.join(directory,_f))
              logger.debug( _f)
    
    toBeFilteredCount=len(files) - maxCount
    for _f in files:
       if maxCount== -1 or toBeFilteredCount < 0 :
          break
       if fnmatch.fnmatch(_f,pattern):
          _filteredfiles.add(os.path.join(directory,_f))
          toBeFilteredCount=toBeFilteredCount-1
          logger.debug( _f)      
    src_size=get_size(directory)/1024
    logger.debug("src size = %dk " ,src_size)
    neededSize= src_size - maxSizeInK
    logger.debug("needed size = %dk",neededSize)
    for _f in files:
       if maxSizeInK== -1 or neededSize < 0 :
          break
       if fnmatch.fnmatch(_f,pattern):
          _filteredfiles.add(os.path.join(directory,_f))
          neededSize=neededSize-get_size(os.path.join(directory,_f))/1024
          logger.debug( _f)      
            
    logger.debug (_filteredfiles)    
    return _filteredfiles



def gzipFilesAndMove(ffiles,target,logger): 
    for _file in ffiles:
       logger.debug( "About to gzip "+_file)
       myfile= open(_file, "r")
       content=myfile.read()
       f = gzip.open(target+ "/"+ ntpath.basename(_file)+"_"+str(time.mktime(datetime.now().timetuple())) +'.gz', 'wb')
       f.write(content)
       f.close()
       os.remove(_file)


def removeFiles(ffiles,logger):
    for _file in ffiles:
        logger.debug("About to removing "+ _file) 
        os.remove(_file)
    logger.debug("done. " ) 

def setFileDevNull(ffiles,logger):
    for _file in ffiles:
      logger.debug("About to set to /dev/null  "+ _file) 
      fo = open(_file, "wb")
      devnull = open(os.devnull, 'w')
      fo = devnull
      fo.close()
      devnull.close()
 


def deleteDirs(dirs,logger):
    for _dir in dirs:
      logger.debug("About to remove dir = "+ _dir ) 
      shutil.rmtree(_dir,ignore_errors=True) 

def moveFiles(ffiles,target,logger): 
    for _file in ffiles:
        logger.debug("about to move "+ _file)
        shutil.move(_file, target)

def main():  
    if len(sys.argv)>1:
       settingsFile = sys.argv[1]
       if os.path.isfile(settingsFile):
           DOMTree = xml.dom.minidom.parse(settingsFile)
           root = DOMTree.documentElement
           # Get all the logger  settings
           logSettings = root.getElementsByTagName("logSettings")
           for logSetting in logSettings:
              LOG_FILENAME =logSetting.getElementsByTagName('location')[0].childNodes[0].data.strip()
              maxSizeInK =logSetting.getElementsByTagName('maxSizeInK')[0].childNodes[0].data.strip()
              maxCount =logSetting.getElementsByTagName('maxCount')[0].childNodes[0].data.strip()
              level =logSetting.getElementsByTagName('level')[0].childNodes[0].data.strip()
           

           logger = logging.getLogger('rotator')
           logger.setLevel(int(level))
           handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=int(maxSizeInK)*1024, backupCount=int(maxCount))
           formatter = logging.Formatter('%(asctime)s  - %(levelname)s - %(message)s')
           handler.setFormatter(formatter)
           logger.addHandler(handler)
           logger.info ("logger has started successfully. ")

          
           # Get all the locations  settings
           locations = root.getElementsByTagName("location")
           # Print detail of each location.
           
           for location in locations:
              logger.debug( "*****location*****")
           
              if location.hasAttribute("src"): 
                  src = location.getAttribute("src")
                  logger.debug("src=" + src  )

              
              filters = location.getElementsByTagName('filters')
             

              for fil in filters:
                   if fil.hasAttribute("pattern"): 
                      pattern = fil.getAttribute("pattern")
                      logger.debug("pattern= " + pattern  )
                   if fil.hasAttribute("type"): 
                      ftype = fil.getAttribute("type")
                      logger.debug("type= " + ftype  )
                   expireAgeInMin =int( fil.getElementsByTagName('expireAgeInMin')[0].childNodes[0].data.strip()) 
                   logger.debug("expireAgeInMin= %d M" , expireAgeInMin)
                   maxCount = int(fil.getElementsByTagName('maxCount')[0].childNodes[0].data.strip())
                   logger.debug("maxCount= %d " ,maxCount)
                   maxSizeInK = int(fil.getElementsByTagName('maxSizeInK')[0].childNodes[0].data.strip())
                   logger.debug("maxSizeInK= %dk" ,maxSizeInK)

              ffiles=getFilteredFiles(src,pattern,expireAgeInMin,maxCount,maxSizeInK,logger)

              actions = location.getElementsByTagName('actions')
              for action in actions:
                   if action.getElementsByTagName('setNull'):
                      logger.debug("Actions :: setNull")
                      setFileDevNull(ffiles,logger)        
                   elif action.getElementsByTagName('delete'):
                      logger.debug("Actions :: delete")
                      if ftype  =="file":
                         removeFiles(ffiles,logger)
                      elif ftype  =="dir":
                         deleteDirs(ffiles,logger)
                   elif action.getElementsByTagName('move'):
                      target= action.getElementsByTagName('move')[0].childNodes[0].data.strip()
                      logger.debug("Actions :: move " + target)
                      moveFiles(ffiles,target,logger)
                   elif action.getElementsByTagName('gzipAndMove'):
                      target = action.getElementsByTagName('gzipAndMove')[0].childNodes[0].data.strip()
                      logger.debug("Actions :: gzipAndMove " + target)
                      gzipFilesAndMove(ffiles,target,logger)
 
       else:
           logger.error('settings file dose not exist, Please validate: ' + args.settings[0])
           logger.error('Exit !')
           sys.exit(0)
    
if __name__ == "__main__":
    main()
