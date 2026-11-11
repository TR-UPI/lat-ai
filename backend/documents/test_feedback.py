from copy import deepcopy
from uuid import uuid4

from django.test import TestCase

from .models import StudyPack
from .study_schema import InvalidStudyResult, check_result
from .test_study import BASE, SOURCE, StudyApiFixture
from .test_study_jobs import result


class StudyFeedbackTests(StudyApiFixture, TestCase):
    def enriched(self):
        payload=result()
        payload['questions'][0]['option_explanations']=[
            'This option confuses the two concepts.',
            'This option applies the definition correctly.',
            'This describes a different operation.',
            'This adds a condition the source does not support.',
        ]
        return payload

    def test_selected_feedback_and_key_are_exposed_only_after_submission(self):
        document=self.upload().data['id']
        pid=self.generate(BASE+str(document)+'/').data['id']
        StudyPack.objects.filter(pk=pid).update(status='ready',result=self.enriched())
        url=BASE+f'packs/{pid}/'
        public=self.client.get(url).data
        self.assertEqual(set(public['questions'][0]),{'id','prompt','options'})
        request={'request_id':str(uuid4()),'question_id':'q1','choice':0}
        response=self.client.post(url+'attempts/',request,format='json')
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['feedback'],'This option confuses the two concepts.')
        self.assertEqual(response.data['correct_option'],'Two')
        self.assertEqual(response.data['score'],0)
        self.assertNotIn('option_explanations',response.data)
        self.assertEqual(response.data,self.client.post(url+'attempts/',request,format='json').data)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url+'attempts/',request,format='json').status_code,404)

    def test_validator_supports_legacy_and_enriched_results(self):
        self.assertEqual(check_result(result(),'test',SOURCE),result())
        payload=self.enriched()
        self.assertEqual(check_result(payload,'test',SOURCE),payload)

    def test_invalid_option_explanations_are_rejected(self):
        for bad in ([], ['a']*3, ['a']*5, 'not an array', [None]*4, ['x'*501]*4, ['\x00']*4):
            with self.subTest(bad=repr(bad)[:30]):
                payload=self.enriched()
                payload['questions'][0]['option_explanations']=bad
                with self.assertRaises(InvalidStudyResult):check_result(payload,'test',SOURCE)
