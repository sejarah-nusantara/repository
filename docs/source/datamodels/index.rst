
Data Models
===============================

.. _datamodel_scans:

Scans
-----


  * "notnull" means that the value cannot be NULL
  *  "system-generated" means that the system generates the value, and so it cannot be (directly) manipulated by the user.
  *  All fields that are not "system-generated" can be modified directly by the user via the API :ref:`api_scans`

  * *[DC]* denotes that it is an element of the DublinCore set, which is documented here: http://dublincore.org/documents/dces/
  * date and datetime fields are represented as http://en.wikipedia.org/wiki/ISO_8601
  * encoding of text is in UTF-8
  * There are some differences with the DSS document of 20120903.


======================  ====================== ========= ================ ==============
name                    type                   notnull?  system-generated  remarks
======================  ====================== ========= ================ ==============
number                  integer                yes       yes              This is the automatically generated identifier that is used to identify the scan
archive_id              integer                yes                        Must be an id from the list at ``/lists/archives``. archive_id and archiveFile are typically used to find the corresponding archive file in the repository
archiveFile             string                 yes
URI                     string
sequenceNumber          number                 yes       yes              denotes the order within the file. Can be modified by user input using the "move" call.
folioNumber             string
title                   string
timeFrameFrom           string [1]_                                       timeFrameFrom should be smaller than timeFrameTo
timeFrameTo             string [1]_
subjectEN               string
transcription           memo
transcriptionAuthor     string
transcriptionDate       date
translationEN           memo
translationENAuthor     string
translationENDate       date
translationID           memo
translationIDAuthor     string
translationIDDate       date
type                    string                                            [DC]
language                string                                            [DC] values as http://www.ietf.org/rfc/rfc4646.txt, i.e. 'en', 'id', 'nl'. Default is 'nl'
relation                string                                            [DC]
source                  string                                            [DC]
creator                 string                                            [DC]
date                    datetime                                          [DC]
format                  string                                            [DC]
contributor             string                                            [DC]
publisher               string                                            [DC]
rights                  string                                            [DC]
status                  integer                                           status in the workflow - a value among those listed below
======================  ====================== ========= ================ ==============

.. _status_values:

Status Values
--------------


The status field of the Scan model implements the workflow. It has the following values:

========== =====================================================
id         description
========== =====================================================
0          Deleted (i.e. only accessible when accessed directly)
1          Newly added **default**
2          Public
========== =====================================================

.. _ead_lists:

EAD files
--------------

======================  ====================== ========= ================ ==============
name                    type                   notnull?  system-generated  remarks
======================  ====================== ========= ================ ==============
ead_id                  string                 yes       yes              this value is extracted from the XML file
archive_id              integer                yes                        an archive_id among :ref:`service_archivefile_collection`
archive                 sting                  yes       yes              the name of the archiveid
title                   string                           yes              this value is extracted from the XML file (see :ref:`this table <datamodel_eadfile_xpaths>`)
language                string                           yes              this value is extracted from the XML file (see :ref:`this table <datamodel_eadfile_xpaths>`)
institution             string                           yes              this value is extracted from the XML file (see :ref:`this table <datamodel_eadfile_xpaths>`)
dateLastModified        string                 yes       yes              this value is extracted from the XML file (see :ref:`this table <datamodel_eadfile_xpaths>`)
findingaid              string                           yes              this value is extracted from the XML file (see :ref:`this table <datamodel_eadfile_xpaths>`)
status                  integer                                           a value among the status values :ref:`status_values`
======================  ====================== ========= ================ ==============

Some of these attributes are extracted from the XML file using the following specifications:

.. _datamodel_eadfile_xpaths:

============ ============================================================ =================================================
attribute    where                                                        description
============ ============================================================ =================================================
institution  the value of the attribute ``repositorycode`` of             Identification of an archival institution as repository of a
             ``/ead/archdesc/did/unitid``                                 physical archive
archive      the text value of ``/ead/archdesc/did/unitid``               Identification of an archive
archiveFile  the text values of
             ``/ead/archdesc/..../c#[@level="file"]/did/unitid/``         Identification of an archive file (inventory number)
             where "c#" is one of ``c``, ``c01``, ``c02`` ... ``c09``.
country      the value of the attribute ``countrycode`` of                Country code of an archival institution
             ``/ead/archdesc/did/unitid``
findingaid   the text value of ``/eadheader/eadid>``                      identification of the finding aid
language     the value of the attribute ``langcode`` in                   Language of the finding aid
             ``/ead/eadheader/profiledesc/langusage/language``
???          the value of the attribute ``langcode`` in                   Language of the material
             ``/ead/archdesc/did/langmaterial/language``
============ ============================================================ =================================================

.. _datamodel_archivefile:

Archive files
-------------------

An Archive File is a collection of scans with some meta data.  
It is uniquely identified by an archive_id (cf. :ref:`api_archive`) 
and a string field called (confusingly) "archiveFile".


======================  ====================== ========= ================ ==============
name                    type                   notnull?  system-generated  remarks
======================  ====================== ========= ================ ==============
id                      string                           yes              is generated as {archive_id}/{archiveFile}
archive_id              integer                yes       
archiveFile             string
status                  integer                                           a value among the status values :ref:`status_values`
======================  ====================== ========= ================ ==============
   

How scans are linked to archive files
--------------------------------------

Scans are part of collections called :ref:`datamodel_archivefile`. 

Scans are linked to components in the EAD files by the fields ``archive_id`` and ``archiveFile``.

**note that scans can be linked to more than a single EAD file - we may have different translations**

Log Entries
------------

Log entries are created automatically. They can be searched via API :ref:`api_log`

======================  ================ ==============
name                    type             remarks
======================  ================ ==============
message                 string           ``create``, ``update``, ``delete``
user                    string
date                    datetime
objects                 list             a list of 'links' to objects. These are local paths to objects, such as /scans/1234 or /ead/somefile.xml
======================  ================ ==============


Notes
---------------------------------


.. [1] | The data type is string, but only strings that represent valid date (or partial dates) will be accepted.
