# - coding: utf-8 -
from sqlalchemy import *
from migrate import *

pre_meta = MetaData()
post_meta = MetaData()
archive_table = Table('archive', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('country_code', Text),
    Column('institution', Text),
    Column('institution_description', Text),
    Column('archive', Text),
    Column('archive_description', Text),
)

ARCHIVES = [
    (1,'ID','ID-ANRI','Arsip Nasional Republik Indonesia','K.66a','Archief van de Gouverneur Generaal en Raden van Indie (Hoge Regering) van de VOC en Taakopvolgers',),
    (2,'ID','ID-ANRI','Arsip Nasional Republik Indonesia','K.4','Krawang 1803-1891',),
    (3,'ID','ID-ANRI','Arsip Nasional Republik Indonesia','C.1','Collection of published Daily Journals',),
    (4,'GH', 'GH-PRAAD','Public Records and Archives Administration Department Ghana','MFA','Ministry of Foreign Affairs Archives',),
    (5,'ZA', 'ZA-NARSSA','National Archives and Records Service of South Africa','ALTC','ARCHIVES OF THE TRANSVAAL ASIATIC LAND TENURE ACT COMMITTEE',),
    (6,'BR', 'BR-RJANRIO','Arquivo Nacional Brasil','EG','Junta da Fazenda da Província de Sao Paulo',),
    (7,'IN', 'IN-ChTNA','Chennai Tamil Nadu Archives','DR','Voorlopige inventaris van de archieven van de VOC - kantoren Malabar, Coromandel, Surat en Bengalen en rechtsopvolgers ',),
    (8, 'NL', 'NL-HaNa','National Archives of the Netherlands','K23025', 'Oost-Indische troepen'),
    (9, 'NL', 'NL-HaNa','National Archives of the Netherlands','K23027','Hollandse Divisie Parijs'),
]


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['archive'].create()
    for archive in ARCHIVES:
        migrate_engine.execute(archive_table.insert(archive))


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['archive'].drop()

