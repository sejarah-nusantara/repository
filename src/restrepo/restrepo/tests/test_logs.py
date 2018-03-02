from base import BaseRepoTest, localurl
from restrepo.config import ERRORS


class TestLogs(BaseRepoTest):

    def setUp(self):
        super(TestLogs, self).setUp()
        self.thescan = self.add_one_scan().json

    def test_log_parameter_validation(self):
        """
        Valid parameters are:
            user, date_from, date_to, object_id, object_type
        """
        log_result = self.app.get('/log', {'an_invalid_field': 'value'},
                                  status=400)
        self.assertEqual(len(log_result.json['errors']), 1)
        log_result = self.app.get('/log', {'date_from': '2012-13-13'},
                                  status=400)
        self.assertEqual(len(log_result.json['errors']), 1)
        self.assertEqual(log_result.json['errors'][0]['name'], 'invalid_parameter')

        log_result = self.app.get('/log',
            {'date_from': '2012-12-12', 'date_to': '2012-01-01'}, status=400)
        self.assertEqual(len(log_result.json['errors']), 1)
        self.assertEqual(log_result.json['errors'][0]['name'], ERRORS.invalid_parameter.name)

#     def test_log_search_start_limit(self):
#         log_result = self.app.get('/log', {'start': 1})
#         self.assertEqual(len(log_result.json['results']), 0)
#         log_result = self.app.get('/log')
#         self.assertEqual(log_result.json['total_results'], 1)
#         self.assertEqual(len(log_result.json['results']), 1)
#         self.add_one_scan()
#         log_result = self.app.get('/log', {'start': 0, 'limit': 1})
#         self.assertEqual(len(log_result.json['results']), 1)

#     def test_object_type_validation(self):
#         log_result = self.app.get('/log', {'object_type': 'nonsense'},
#                                   status=400)
#         self.assertEqual(log_result.json['errors'][0]['name'],  ERRORS.invalid_parameter.name)

#     def test_log_search_obj_id(self):
#         res = self.add_one_scan()
#         log_result = self.app.get('/log', {'object_id': res.json['number']})
#         self.assertEqual(len(log_result.json['results']), 1)
#
#     def test_log_search_obj_type(self):
#         self.add_one_scan()
#         self.add_one_ead()
#         log_result = self.app.get('/log', {'object_type': 'ead'})
#         self.assertEqual(len(log_result.json['results']), 1)
#         log_result = self.app.get('/log', {'object_type': 'scan'})
#         self.assertEqual(len(log_result.json['results']), 2)

#     def test_log_search_by_date(self):
#         sleep(0.1)
#         before = datetime.utcnow()
#         # wait a little bit: the resolution of datetime is not enough
#         # for this fast test
#         sleep(0.1)
#         put_res = self.add_one_scan()
#         sleep(0.1)
#         after = datetime.utcnow()
#         log_result = self.app.get('/log', {
#             'date_from': before.isoformat(),
#             'date_to': after.isoformat(),
#         })
#         # Only the newest scan (not the one added in setUp) should show up
#         self.assertEqual(log_result.json['total_results'], 1)
#         res = log_result.json['results']
#         self.assertEqual(len(res), 1)
#         self.assertEqual(int(res[0]['object_id']), put_res.json['number'])
#         self.assertEqual(res[0]['object_type'], 'scan')

#     def test_log_moved_scan(self):
#         """
#         Moving a scan modifies all scans from its original place
#         to its final destination. S=Source, D=Destination

#         +---+---+---+---+---+---+
#         |   | S | + | + | D |   |
#         +---+---+---+---+---+---+

#         Moving from S to D results in 4 modified scans.
#         Thus there will be 4 entries in the logs.
#         """
#         self.add_five_scans()
#         scans = self.app.get('/scans').json['results']
#         self.assertEqual(
#             [a['sequenceNumber'] for a in scans], [1, 2, 3, 4, 5, 6])
#         url = localurl(scans[1]['URL']) + '/move'
#         self.app.post(url, {'after': 5, 'user': 'someone'})
#         log_result = self.events_log
# #         log_result = self.app.get('/log', {'user': 'someone'})
#         self.assertTrue(log_result)
#         self.assertEqual(len([event for event in log_result if event['user'] == 'someone']), 4)

#         log_result = [event for event in log_result if event['message'] == 'move']
#         self.assertEqual(len(log_result), 4)

        # The date those objects were modified should be unique
        # since it was an atomic operation.
#         dates = [a['date'] for a in log_result]
#         self.assertEqual(len(set(dates)), 1)

    # def test_log_delete(self):
    #     "Ensure delete operations are logged correctly"
    #     url = localurl(self.thescan['URL'])

    #     self.reset_events_log()
    #     self.app.delete(url, {'user': 'adeleter'})
    #     # Ensure it was logged
    #     log_result = self.events_log

    #     self.assertEqual(len(log_result), 1)
    #     log = log_result[0]
    #     self.assertEqual(log['object_type'], 'scan')
    #     self.assertEqual(log['message'], 'delete')
    #     self.assertEqual(str(log['object_id']), str(self.thescan['number']))

    # def test_log_update_scan(self):
    #     "When a scan is updated a log entry is created"
    #     self.reset_events_log()
    #     url = localurl(self.thescan['URL'])
    #     self.app.put(url, {'status': 1, 'user': 'me'})
    #     log_result = self.events_log
    #     self.assertEqual(len(log_result), 1)
    #     log = log_result[0]
    #     self.assertEqual(log['object_type'], 'scan')
    #     self.assertEqual(log['message'], 'update')

    # def test_log_create_ead(self):
    #     self.add_one_ead()
    #     logs = self.events_log
    #     self.assertEqual(len(logs), 2)
    #     self.assertEqual(logs[0]['object_type'], 'scan')
    #     self.assertEqual(logs[0]['message'], 'create')
    #     self.assertEqual(logs[1]['object_type'], 'ead')
    #     self.assertEqual(logs[1]['message'], 'create')

    # def test_log_delete_ead(self):
    #     ead = self.add_one_ead().json
    #     self.reset_events_log()
    #     self.app.delete(localurl(ead['URL']))
    #     logs = self.events_log
    #     self.assertEqual(len(logs), 1)
    #     self.assertEqual(logs[0]['object_id'], ead['ead_id'])

    # def test_log_update_ead(self):
    #     ead = self.add_one_ead().json
    #     url = localurl(ead['URL'])
    #     self.app.put(url, {'status': 1, 'user': 'me'})
    #     logs = self.events_log
    #     self.assertEqual(len(logs), 3)
    #     self.assertEqual(logs[0]['object_type'], 'scan')
    #     self.assertEqual(logs[1]['object_type'], 'ead')
    #     self.assertEqual(logs[2]['object_type'], 'ead')
    #     self.assertEqual(logs[2]['message'], 'update')

#     def test_search_validate_sort(self):
#         self.app.get('/log', {'order_by': 'wrong'}, status=400).json
#         self.app.get('/log', {'order_dir': '--'}, status=400).json
#         self.app.get('/log', {'order_by': 'user'}).json
#         self.app.get('/log', {'order_dir': 'ASC'}).json
#         self.app.get('/log', {'order_dir': 'DESC'}).json
#
#     def test_search_sort(self):
#         self.add_one_scan(dict(self.scan_data, user='foo')).json
#         bar = self.add_one_scan(dict(self.scan_data, user='bar')).json
#         results = self.app.get('/log',
#             {'order_by': 'user', 'order_dir': 'ASC'}).json['results']
#         self.assertEqual(int(results[0]['object_id']), bar['number'])
#         results = self.app.get('/log',
#             {'order_by': 'user', 'order_dir': 'DESC'}).json['results']
#         self.assertEqual(int(results[-1]['object_id']), bar['number'])

#     def test_updating_scan_logs_all_modified_scans(self):
#         """
#         When we update a scan changing its archive_id or archiveFile
#         as a side effect many scans can be updated.
#         They will all be present in logs.
#         """
#         set1, set2 = [], []
#         for _i in range(3):
#             set1.append(self.add_one_scan(self.scan_data).json)
#         set2_data = dict(self.scan_data, archiveFile='foo')
#         for _i in range(3):
#             set2.append(self.add_one_scan(set2_data).json)
#         # We have two sets of scans. We move the second scan from set1 to set2
#         url = localurl(set1[1]['URL'])
#         self.app.put(url, dict(archiveFile='foo'))
#         logs = self.events_log
#         move_logs = [event for event in logs if event['message'] == 'move']
#         self.assertEqual(len(move_logs), 1)
# #         move_logs = self.app.get('/log', {'message': 'move'}).json
# #         self.assertEqual(move_logs['total_results'], 1)
