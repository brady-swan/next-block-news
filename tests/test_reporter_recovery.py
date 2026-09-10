import json
import threading
import unittest
from unittest.mock import Mock, patch
from nbn import config, reporter_api as api, reporter_store as rs, reporter_delivery as delivery, reporter_remote as remote, store
from tests.support import temporary_store
from tests.test_reporter_delivery import ReporterDeliveryTests


class ReporterRecoveryTests(unittest.TestCase):
    def test_cross_key_unknown_post_still_blocks_exact_copy(self):
        fixture=ReporterDeliveryTests()
        with temporary_store() as con,fixture.stack():
            shift=fixture.begin(con)
            import httpx
            with patch.object(delivery.httpx,'post',side_effect=httpx.ReadTimeout('lost')):
                delivery.submit(con,shift_id=shift['shift_id'],generation=shift['generation'],submission_id='one',payload=fixture.payload())
                with self.assertRaisesRegex(ValueError,'uncertain delivery'):
                    delivery.submit(con,shift_id=shift['shift_id'],generation=shift['generation'],submission_id='two',
                                    payload={**fixture.payload(),'event_key':'different'})

    def test_crash_after_intent_recovers_without_post(self):
        fixture=ReporterDeliveryTests()
        with temporary_store() as con,fixture.stack():
            shift=fixture.begin(con)
            prepare=store.prepare_publisher_mutation
            def crash(*a,**k):
                prepare(*a,**k)
                raise RuntimeError('simulated process stop after committed intent')
            with patch.object(store,'prepare_publisher_mutation',side_effect=crash):
                with self.assertRaises(RuntimeError):
                    delivery.submit(con,shift_id=shift['shift_id'],generation=shift['generation'],submission_id='crash',payload=fixture.payload())
            with patch.object(delivery.httpx,'post') as post:
                result=delivery.reconcile(con,'crash')
                self.assertEqual(result['state'],'awaiting_media')
                self.assertTrue(result['mutation_id']);post.assert_not_called()

    def test_pause_serializes_against_final_dispatch(self):
        with temporary_store() as con:
            rs.start(con,worker_id='local',shift_id='shift')
            acquired=threading.Event(); release=threading.Event()
            def dispatch():
                with rs.dispatch_lock: acquired.set();release.wait(2)
            thread=threading.Thread(target=dispatch);thread.start();acquired.wait(1)
            timer=threading.Timer(.05,release.set);timer.start()
            result=rs.stop(con,'shift')
            self.assertTrue(release.is_set());self.assertEqual(result['status'],'paused');thread.join()

    def test_delivered_reply_acknowledges_only_matching_shift(self):
        from nbn import reporter_tools
        with temporary_store() as con:
            shift=rs.start(con,worker_id='local',shift_id='s')
            api.dispatch(con,'POST','message','control',{'shift_id':'s','record_id':'msg1','payload':{'text':'lead'}})
            api.dispatch(con,'POST','delivered','control',{'shift_id':'s','turn_id':'turn1','record_ids':['msg1']})
            reporter_tools.dispatch(con,shift_id='s',generation=shift['generation'],name='nbn_note',
                args={'record_id':'reply1','kind':'message','reply_to':'msg1','payload':{'text':'Read it'}})
            self.assertIsNotNone(con.execute("SELECT acknowledged_at FROM reporter_records WHERE record_id='msg1'").fetchone()[0])

    def test_deleted_tracked_draft_is_read_back_and_cleared(self):
        fixture=ReporterDeliveryTests()
        with temporary_store() as con,patch.multiple(config,TYPEFULLY_API_KEY='test',TYPEFULLY_SOCIAL_SET_ID='1'),patch.object(remote,'MORNING_BASELINE',()):
            remote.capture(con,fixture.raw())
            with con: con.execute("INSERT INTO posts(created,body,mode,nuelink_id,publisher_backend,publisher_status) VALUES (0,'copy','DRAFT','123','typefully','draft')")
            response=Mock();response.json.return_value={'results':[],'next':None}
            with patch.object(remote.httpx,'get',return_value=response),patch.object(remote.tf,'get_draft',return_value={'id':123,'status':'deleted'}) as get:
                remote.synchronize(con,force=True)
            get.assert_called_once_with('123')
            self.assertEqual(con.execute('SELECT publisher_status FROM posts').fetchone()[0],'deleted')
