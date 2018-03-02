.. _api_scans:

Scans
=================

Scans are images together with some metadata. 

Scans are often part of an :ref:`api_archivefile`.

The services offered allow for creating, updating and deleting scans, changing the order of scans, 
accessing the original image, and returning that image in specified sizes.


.. services::  
   :modules: restrepo.browser.scans
   :services: service_scan_collection, service_scan_item, service_scan_images_collection, service_scan_images_item, service_scan_images_item_raw, service_default_scan_image, move_scan,  scan_list_institutions, scan_list_archiveFiles




   