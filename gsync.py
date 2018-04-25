#!/usr/bin/env python
# Copyright 2018 Bateared Collie
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this 
#   list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this 
#   list of conditions and the following disclaimer in the documentation and/or other
#   materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may 
#   be used to endorse or promote products derived from this software without specific
#   prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY 
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT 
# SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT 
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR 
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
'''
Defines classes and methods for assiting in google drive synchronisation
'''

import sys
import os
import sqlite3
import subprocess
import re

run_methods=[
    ('add','adds a folder file id pair'),
    ('delete','removes a folder file id pair'),
    ('push','sync upload'), 
    ('pull','sync download'),
    ('list','list sync directories'),
    ('help','print this message')    
    ]

delete_methods =[
    ('id','database id'),
    ('path','folder path'),
    ('gid','Google file ID'),     
    ]

def list_methods():
    '''
    return a list of methods
    '''
    out =[]
    for nm,tt in run_methods: out.append(nm)
    return out

def list_delete_methods():
    '''
    return a list of methods
    '''
    out =[]
    for nm,tt in delete_methods: out.append(nm)
    return out

def make_help_string():
    '''
    Returns the help string
    '''
    
    ss = """

Usage: gsync <method> [options]

Type 'gsync <method> help' for help on a specific method.

Gsync is a tool for syncing a set of directories with corresponding file 
Ids on Google drive. All the hard work is done through calls to gdrive.


Available methods:

"""

    for nm,desc in run_methods: ss += "   * "+nm+":\t"+desc+'\n'

    ss += """

"""
    return ss

def make_help_string_add():
    '''
    Makes the help string for the run command
    '''

    ss = """
    
Usage: gsync add  [folder] [google_file_id] 

"""
    return ss

def make_help_string_list():
    '''
    Makes the help string for the list command
    '''

    ss = """
    
Usage: gsync list 
"""
    return ss

def make_help_string_delete():
    '''
    Makes the help string for the delete command
    '''

    ss = """
    
Usage:\n"""
    for nm,desc in delete_methods: ss += "   gsync delete "+nm+" ["+desc+"]\t -delete "+desc+"\n"
    ss +="\n"
    return ss

def make_help_string_push():
    '''
    Makes the help string for the push command
    '''

    ss = """
    
Usage: gsync push [-gdrive_opt1] [[-gdrive_opt2] ...
"""
    return ss

def open_database():
    '''
    Opens the internal database creating if necessary
    '''
    
    dbfile = os.environ["HOME"]+"/.gsync.db"
    olddb=os.path.exists(dbfile)
    db = sqlite3.connect(dbfile)

    if olddb == False:
        cursor = db.cursor()
        cursor.execute('''
        CREATE TABLE sync_list (id INTEGER PRIMARY KEY AUTOINCREMENT,folder TEXT, google_id TEXT)
        ''')
        db.commit()
        
    return db

def get_info(gid):
    '''
    Get the google ID file info
    '''
    cmnd = "gdrive info "+gid    
    proc= subprocess.Popen(cmnd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
 
    info={}
    for line in proc.stdout: 
        kk,dta = line.replace("\n","").split(":",1)
        info[kk]=dta.lstrip(' ')
    
    return info   

def check_googleID_exists_and_is_directory(gid):
    '''
    Function to check a google ID exists and is a directory
    '''
    
    info=get_info(gid)
    
    if info["Mime"] != "application/vnd.google-apps.folder": 
        print "\nRequested sync google ID is not a directory, check the info and view URL"
        for kk in info: print "\t",kk," : ",info[kk]
        return False
    
    return True

def list_folder(gid):
    '''
    Lists files in a directory, note this only provides a list of immediate children
    '''
    cmnd = "gdrive list -q \"'"+gid+"' in parents\" --no-header --name-width 0 -m 9999 --order 'modifiedTime desc'"
    proc= subprocess.Popen(cmnd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    list = {"gid":[],"name":[],"type":[],"size":[],"date-created":[]}
    for line in proc.stdout: 
        line=line.replace("\n","")
        arr = line.split()
        list["gid"].append(arr[0])
        list["name"].append(arr[1])
        list["type"].append(arr[2])
        if len(arr)==5: 
            list["size"].append(None)
            dt =  arr[3]+" "+arr[4]     
        else:
            list["size"].append(arr[3])
            dt =  arr[4]+" "+arr[5]  
        list["date-created"].append(dt)
        
    return list

def make_new_directory(parent_gid,name):
    '''
    Make a new directory and return the ID
    '''
    
    print "\nMaking new directory"
    cmnd = "gdrive mkdir -p "+parent_gid+" "+name
    subprocess.check_call(cmnd,shell=True)
    
    list = list_folder(parent_gid)
    
    for gid,nn in zip(list["gid"],list["name"]):
        if nn == name: return gid
    sys.exit("Tried to create directory '"+name+"' in "+parent_gid+" but could not get the resulting file ID")
      
def empty_folder_check(gid,folder):
    '''
    gdrive requires that the first sync action is to upload to an empty folder
    '''
    
    # check folder is empty
    flist=list_folder(gid)
    if len(flist)!=0:
        info = get_info(gid)

        print "\nThe sync folder "+gid+" is not empty going to make a new folder and set the sync process to work with that"        
        print "Folder info:"
        for kk in info: print "\t",kk," : ",info[kk]
    
        ## Make a temp directory in the parent 
        new_gid = make_new_directory(info["Parents"],info["Name"]+"-gsync")
        new_info = get_info(new_gid)
        
        ## Run an upload sync
        print "\nCreated new folder ",info["Name"]+"-gsync"," : ",new_gid,"  running first upload sync"
        cmnd = "gdrive sync upload "+folder+" "+new_gid
        subprocess.check_call(cmnd,shell=True)
        
        ## Download the files into the new folder (removing from old location)
        print "\nDownloading files form the old folder"
        cmnd = "gdrive download "+gid+" --recursive --path "+folder.rstrip('/')
        print "cmnd: ",cmnd
        subprocess.check_call(cmnd,shell=True) 
    
        #Correct the locations
        cmnd = "mv -i "+folder+"/"+info["Name"]+"/* "+folder+"/ ; rm -r "+folder+"/"+info["Name"]
        print "cmnd: ",cmnd
        subprocess.check_call(cmnd,shell=True) 

        ## Sync upload again
        print "\nRunning sync upload again."
        cmnd = "gdrive sync upload "+folder+" "+new_gid
        print "cmnd: ",cmnd
        subprocess.check_call(cmnd,shell=True)                
                
        print "\nThe local directory "+folder+" has now been synced with drive folder :",new_gid,\
                " and the contents for the old folder:"
        print "\t ",info["Name"]," at ",info["ViewUrl"]
        print "have been copied to  the new location: "
        print "\t ",new_info["Name"]," at ",new_info["ViewUrl"]        

        return new_gid
    
    return gid 
 
def run_add(args):
    '''
    Runs the add 
    '''

    if "help" in args:
        print make_help_string_add()        
        return 
    
    if os.path.exists(args[0])==False:
        print "ERROR: Path ",args[0]," does not exist\n"
        print make_help_string_add()        
        return 
     
    folder = os.path.abspath(args[0])
    googleID = args[1]
    
    # Check google ID exists  and is a diretcory 
    if check_googleID_exists_and_is_directory(googleID)!=True:
        sys.exit("Trying to add sync folder "+googleID+" but this id does not exist or is not a directory")
    
    # Check is empty 
    sync_id=empty_folder_check(googleID,folder)
    
    # Open the database
    db = open_database()
    
    # Add to Database
    cursor = db.cursor()
    
    cursor.execute('''INSERT INTO sync_list(folder, google_id)
                  VALUES(?,?)''', (folder,sync_id))    
    db.commit()

    db.close()

def run_list(args):
    '''
    Runs the list command
    '''
    
    if "help" in args:
        print "\n"+make_help_string_list()        
        return 

    # Open the database
    db = open_database()
    
    cursor= db.cursor()
    cursor.execute('''SELECT id,folder, google_id from sync_list order by id''')
    rows = cursor.fetchall()
    print "id : Folder : Google ID"
    print "-------------------------------"
    for row in rows:
        ii,ff, gg = row
        print ii," : ",ff," : ",gg
    print "-------------------------------"
    print "Total : ",len(rows)
            
    db.close()

def run_delete_id(id):
    '''
    Deletes and Id from the database
    ''' 
    db = open_database()
    cursor = db.cursor()    
    cursor.execute("delete from sync_list where id=?",(id,))
    db.commit()
    db.close()
    return

def run_delete_path(path):
    '''
    Deletes and Id from the database
    ''' 
    db = open_database()
    cursor = db.cursor()
    cursor.execute("delete from sync_list where folder=?",(path,))
    db.commit()
    db.close()
    return

def run_delete_gid(gid):
    '''
    Deletes and Id from the database
    ''' 
    db = open_database()
    cursor = db.cursor()
    cursor.execute("delete from sync_list where google_id=?",(gid,))
    db.commit()
    db.close()
    return

def run_delete(args):
    '''
    Runs the delete 
    '''

    if "help" in args:
        print make_help_string_delete()        
        return 
    
    if args[0] not in list_delete_methods():
        print "\nERROR: Unrecognized deletion method: "+args[0]+"\n"
        print make_help_string_delete()        
        return 
    
    if args[0]=="id":
        run_delete_id( args[1])    
    elif args[0]=="path":
        run_delete_path( args[1])          
    elif args[0]=="gid":
        run_delete_gid( args[1])     
    else:
        print "\nERROR: Unrecognised deletion method\n"
        print make_help_string_delete()        
        return         

def run_push(args):
    '''
    Pushes files to google drive
    '''
    if "help" in args:
        print make_help_string_push()        
        return 
    
    # Base command    
    cmnd = "gdrive sync upload"
    for oo in args: cmnd +=" "+oo
    
    # Open the database
    db = open_database()
    cursor= db.cursor()
    
    # Work though the rows in the data base
    cursor.execute('''SELECT folder, google_id from sync_list order by id''')
    rows = cursor.fetchall()
    for folder, gid in rows:
        
        # Construct command 
        cc = cmnd+" "+folder+" "+gid
        print "\ncmnd: ",cc
        
        # Execute
        subprocess.check_call(cc,shell=True)
                    
    db.close()

def run_pull(args):
    '''
    Pulls files from google drive
    '''
    if "help" in args:
        print make_help_string_push()        
        return 
    
    # Base command    
    cmnd = "gdrive sync download"
    for oo in args: cmnd +=" "+oo
    
    # Open the database
    db = open_database()
    cursor= db.cursor()
    
    # Work though the rows in the data base
    cursor.execute('''SELECT folder, google_id from sync_list order by id''')
    rows = cursor.fetchall()
    for folder, gid in rows:
        
        # Construct command 
        cc = cmnd+" "+gid+" "+folder
        print "\ncmnd: ",cc
        
        # Execute
        subprocess.check_call(cc,shell=True)
                    
    db.close()

def run(call,args):
    '''
    Runs a call
    '''
    
    if call == 'add':
        run_add(args)
    elif  call == 'list':
        run_list(args)
    elif call == 'delete':
        run_delete(args)    
    elif call == 'push':
        run_push(args)
    elif call == 'pull':
        run_pull(args)
    else:
        print "\nERROR: Unrecognised method "+call+"\n"
        print make_help_string()        
        return  

if __name__ == "__main__":

    print "sys.argv = ",sys.argv

    if len(sys.argv) < 2:
        call = 'help'
    elif "help" in sys.argv[1].lower():
        call = 'help'
    else:
        call = sys.argv[1].lower()

    if call not in list_methods():
        print "\nERROR: Unrecognized method "+call
        call ='help'
    
    if call == 'help':
        print make_help_string()
    else:
        run(call,sys.argv[2:])
