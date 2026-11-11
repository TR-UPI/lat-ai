import re
from rest_framework import serializers

PUBLIC_FIELDS = {'contract_version','request_id','action','question','course_id','lesson_id','exercise_id','mode','document_ids','code_context'}

class TutorAskSerializer(serializers.BaseSerializer):
    """Strict boundary; Node additionally validates Unicode/selection and schema."""
    def to_internal_value(self, data):
        invalid = serializers.ValidationError('INVALID_REQUEST')
        if not isinstance(data, dict) or set(data) - PUBLIC_FIELDS:
            raise invalid
        if data.get('contract_version') != '1.0' or data.get('action') not in ('explain','hint'):
            raise invalid
        if not isinstance(data.get('request_id'), str) or not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', data['request_id']):
            raise invalid
        for key in ('course_id','lesson_id','exercise_id'):
            value = data.get(key)
            if key == 'exercise_id' and value is None:
                continue
            if type(value) is not int or not 0 < value <= 9007199254740991:
                raise invalid
        if not isinstance(data.get('question'), str) or not 0 < len(data['question']) <= 2000:
            raise invalid
        try:
            if len(data['question'].encode('utf-16-le'))//2>2000:
                raise invalid
        except UnicodeEncodeError:
            raise invalid
        if isinstance(data.get('code_context'),dict) and isinstance(data['code_context'].get('code'),str):
            try:
                data['code_context']['code'].encode('utf-16-le')
            except UnicodeEncodeError:
                raise serializers.ValidationError('INVALID_CODE_CONTEXT',code='INVALID_CODE_CONTEXT')
        return dict(data)
