import string
from random import choices

from django.db import models
from mixer.backend.django import Mixer
from rest_framework import serializers
from rest_framework.serializers import ALL_FIELDS
from test_plus.test import TestCase

from .mixins import FieldsManageMixin


class TestClass(object):
    def __init__(self, **kwargs):
        if kwargs.get('major_field', None):
            self.major_field = kwargs.get('major_field')
            self.minor_fields = kwargs.get('minor_fields') or []
        else:
            for field in ('field_1', 'field_2', 'field_3', 'field_4'):
                setattr(self, field, random_srt())


class TestModelClass(models.Model):
    model_field_1 = models.CharField(max_length=10)
    model_field_2 = models.CharField(max_length=10)


def random_srt():
    return ''.join(choices(string.digits + string.ascii_letters, k=10))


test_model_minor = {
    0: TestClass(),
    1: TestClass()
}

test_model_major = {
    0: TestClass(major_field=random_srt(), minor_fields=test_model_minor.values()),
}


class MinorTestSerializer(FieldsManageMixin, serializers.Serializer):
    field_1 = serializers.CharField()
    field_2 = serializers.CharField()


class MajorTestSerializer(FieldsManageMixin, serializers.Serializer):
    major_field = serializers.CharField()
    minor_fields = MinorTestSerializer(many=True)


class ModelTestSerializer(FieldsManageMixin, serializers.ModelSerializer):
    model_field_1 = serializers.CharField()
    model_field_2 = serializers.CharField()
    minor_fields = serializers.SerializerMethodField()

    def get_minor_fields(self, data):
        return MinorTestSerializer(instance=test_model_minor.values(), many=True).data

    class Meta:
        model = TestModelClass
        fields = ('model_field_1',
                  'model_field_2',
                  'minor_fields',)


class ModelTestMetaOnlySerializer(FieldsManageMixin, serializers.ModelSerializer):

    class Meta:
        model = TestModelClass
        fields = ('model_field_1',
                  'model_field_2',)


class FieldsManageMixinTest(TestCase):

    def test_minor_serializer_with_mixin(self):
        minor_serializer = MinorTestSerializer(instance=test_model_minor.values(), many=True)
        self.assertEqual(len(minor_serializer.data), 2)
        self.assertEqual(len(minor_serializer.data[0]), 2)
        self.assertEqual(minor_serializer.data[0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(minor_serializer.data[0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(minor_serializer.data[1]['field_1'], test_model_minor[1].field_1)
        self.assertEqual(minor_serializer.data[1]['field_2'], test_model_minor[1].field_2)

        minor_serializer_include_cls = MinorTestSerializer.include_fields('field_1')
        minor_serializer_include = minor_serializer_include_cls(instance=test_model_minor.values(), many=True)
        self.assertEqual(len(minor_serializer_include.data), 2)
        self.assertEqual(len(minor_serializer_include.data[0]), 1)
        self.assertEqual(minor_serializer_include.data[0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(minor_serializer_include.data[1]['field_1'], test_model_minor[1].field_1)

        minor_serializer_exclude_cls = MinorTestSerializer.exclude_fields('field_1')
        minor_serializer_exclude = minor_serializer_exclude_cls(instance=test_model_minor.values(), many=True)
        self.assertEqual(len(minor_serializer_exclude.data), 2)
        self.assertEqual(len(minor_serializer_exclude.data[0]), 1)
        self.assertEqual(minor_serializer_exclude.data[0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(minor_serializer_exclude.data[1]['field_2'], test_model_minor[1].field_2)

    def test_major_serializer_with_mixin(self):
        major_serializer = MajorTestSerializer(instance=test_model_major.values(), many=True)
        self.assertEqual(len(major_serializer.data), 1)
        self.assertEqual(len(major_serializer.data[0]), 2)
        self.assertEqual(len(major_serializer.data[0]['minor_fields']), 2)
        self.assertEqual(major_serializer.data[0]['major_field'], test_model_major[0].major_field)
        self.assertEqual(major_serializer.data[0]['minor_fields'][0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(major_serializer.data[0]['minor_fields'][0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(major_serializer.data[0]['minor_fields'][1]['field_1'], test_model_minor[1].field_1)
        self.assertEqual(major_serializer.data[0]['minor_fields'][1]['field_2'], test_model_minor[1].field_2)

        major_serializer_include_cls = MajorTestSerializer.include_fields('minor_fields')
        major_serializer_include = major_serializer_include_cls(instance=test_model_major.values(), many=True)
        self.assertEqual(len(major_serializer_include.data), 1)
        self.assertEqual(len(major_serializer_include.data[0]), 1)
        self.assertEqual(len(major_serializer_include.data[0]['minor_fields']), 2)
        self.assertEqual(major_serializer_include.data[0]['minor_fields'][0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(major_serializer_include.data[0]['minor_fields'][0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(major_serializer_include.data[0]['minor_fields'][1]['field_1'], test_model_minor[1].field_1)
        self.assertEqual(major_serializer_include.data[0]['minor_fields'][1]['field_2'], test_model_minor[1].field_2)

        major_serializer_exclude_cls = MajorTestSerializer.exclude_fields('major_field')
        major_serializer_exclude = major_serializer_exclude_cls(instance=test_model_major.values(), many=True)
        self.assertEqual(len(major_serializer_exclude.data), 1)
        self.assertEqual(len(major_serializer_exclude.data[0]), 1)
        self.assertEqual(len(major_serializer_exclude.data[0]['minor_fields']), 2)
        self.assertEqual(major_serializer_exclude.data[0]['minor_fields'][0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(major_serializer_exclude.data[0]['minor_fields'][0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(major_serializer_exclude.data[0]['minor_fields'][1]['field_1'], test_model_minor[1].field_1)
        self.assertEqual(major_serializer_exclude.data[0]['minor_fields'][1]['field_2'], test_model_minor[1].field_2)

    def test_model_serializer_with_mixin(self):
        new_mixer = Mixer(commit=False)
        obj = new_mixer.blend(TestModelClass)

        model_serializer = ModelTestSerializer(instance=obj)
        self.assertEqual(len(model_serializer.data), 3)
        self.assertEqual(len(model_serializer.data['minor_fields']), 2)
        self.assertEqual(model_serializer.data['model_field_1'], obj.model_field_1)
        self.assertEqual(model_serializer.data['model_field_2'], obj.model_field_2)
        self.assertEqual(model_serializer.data['minor_fields'][0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(model_serializer.data['minor_fields'][0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(model_serializer.data['minor_fields'][1]['field_1'], test_model_minor[1].field_1)
        self.assertEqual(model_serializer.data['minor_fields'][1]['field_2'], test_model_minor[1].field_2)

        model_serializer_exclude_cls = ModelTestSerializer.exclude_fields('model_field_1')
        model_serializer_exclude = model_serializer_exclude_cls(instance=obj)
        self.assertEqual(len(model_serializer_exclude.data), 2)
        self.assertEqual(model_serializer_exclude.data['model_field_2'], obj.model_field_2)
        self.assertEqual(model_serializer_exclude.data['minor_fields'][0]['field_1'], test_model_minor[0].field_1)
        self.assertEqual(model_serializer_exclude.data['minor_fields'][0]['field_2'], test_model_minor[0].field_2)
        self.assertEqual(model_serializer_exclude.data['minor_fields'][1]['field_1'], test_model_minor[1].field_1)
        self.assertEqual(model_serializer_exclude.data['minor_fields'][1]['field_2'], test_model_minor[1].field_2)

        model_serializer_include_cls = ModelTestSerializer.include_fields('model_field_1')
        model_serializer_include = model_serializer_include_cls(instance=obj)
        self.assertEqual(len(model_serializer_include.data), 1)
        self.assertEqual(model_serializer_include.data['model_field_1'], obj.model_field_1)

    def test_model_meta_only_serializer_with_mixin(self):
        new_mixer = Mixer(commit=False)
        obj = new_mixer.blend(TestModelClass)

        model_serializer = ModelTestMetaOnlySerializer(instance=obj)
        self.assertEqual(len(model_serializer.data), 2)
        self.assertEqual(model_serializer.data['model_field_1'], obj.model_field_1)
        self.assertEqual(model_serializer.data['model_field_2'], obj.model_field_2)

        model_serializer_include_cls = ModelTestMetaOnlySerializer.include_fields('model_field_1')
        model_serializer_include = model_serializer_include_cls(instance=obj)
        self.assertEqual(len(model_serializer_include.data), 1)
        self.assertEqual(model_serializer_include.data['model_field_1'], obj.model_field_1)

        model_serializer_exclude_cls = ModelTestMetaOnlySerializer.exclude_fields('model_field_1')
        model_serializer_exclude = model_serializer_exclude_cls(instance=obj)
        self.assertEqual(len(model_serializer_exclude.data), 1)
        self.assertEqual(model_serializer_exclude.data['model_field_2'], obj.model_field_2)

    def test_raising_errors(self):
        with self.assertRaises(ValueError) as err:
            MinorTestSerializer.include_fields('wrong_field')
            self.assertTrue('wrong_field do not exist in Meta or declared_fields in ' in str(err.exception))
        with self.assertRaises(ValueError) as err:
            model_serializer = ModelTestSerializer()
            model_serializer.Meta.fields = '__all__'
            model_serializer.include_fields('wrong_field')
        self.assertEqual(str(err.exception), f'{ALL_FIELDS} does not support')
