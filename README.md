
GSync
======


Frustrated with the standard tools for syncing directories between my local machine and google drive. I 
deceided to write this simple script which stores a list of folders and their corresponding 
location google ids. Then when run it either does an upload sync or download sync for each file_id 
loacl directory pair. All the grunt work is done by the command line program gdrive. 

Installation
------------

### Prerequisites

* GDrive - https://github.com/prasmussen/gdrive

###  Building 

```
$ python ./setup.py install --prefix=[install_location]
```

Usage
-----

Print the help message
```
$ gsync help 
```

Print the list sync directories
```
$ gsync list 
```

Add a folder to sync
```
$ gsync add [folder] [google_id] 
```

Sync upload
```
$ gsync push 
```

Sync download
```
$ gsync pull 
```