.. _api_archivefile:

Archive files
=================


Archive files are the units (books, folders) that contain a collection :ref:`api_scans`. 

Archive files are usually part of :ref:`api_archive`, which are described in :ref:`api_ead`.

Archive file objects are created automatically when either 
1) an EAD file contains a reference to an archivefile
or 2) when a scan contains a reference to an archivefile.

An archive file is deleted automatically if no EAD file or scan refers it, and the data of the archive file 
has not been edited by the user.



.. services::  
   :modules: restrepo.browser.archivefile
   :services: service_archivefile_collection, service_archivefile_item,  




   