import re
from typing import Union
from uuid import uuid4

from rest_framework.relations import RelatedField
from rest_framework.serializers import ModelSerializer, ALL_FIELDS, Serializer


def get_params_retrieve(fields: list):
    first_level_fields = []
    next_level_fields = {}

    if not fields:
        return first_level_fields, next_level_fields

    if not isinstance(fields, list):
        # raise ValueError('type data list supports only')
        fields = [a.strip() for a in fields if a.strip()]

    for f in fields:
        if '{' in f:
            first_level, next_level = re.split(r'{.+}', f)[0], re.search(r'[^{}]*{(.+)}$', f).group(1).split(';')
            first_level_fields.append(first_level)
            next_level_fields[first_level] = next_level
        else:
            first_level_fields.append(f)

    first_level_fields = list(set(first_level_fields))
    return first_level_fields, next_level_fields


class FieldsManageMixin(object):

    @classmethod
    def exclude_fields(cls, *args):
        class_name = f'{cls.__name__}_{uuid4().hex}'
        newclass: Union[Serializer, ModelSerializer] = type(class_name, (cls,), {})

        declared_fields = cls._get_declared_fields(newclass)
        declared_fields_list = list(declared_fields.keys())
        meta_fields_list = cls._get_meta_fields(newclass)

        if meta_fields_list:
            cls._check_extra_fields(newclass, set(declared_fields_list+meta_fields_list), *args)
            newclass.Meta.fields = [field_name for field_name in newclass.Meta.fields if field_name not in args]
        else:
            cls._check_extra_fields(newclass, declared_fields_list, *args)

        for field in declared_fields_list:
            if field in args:
                del declared_fields[field]

        return newclass

    @classmethod
    def include_fields(cls, *args):
        first_level_fields, next_level_fields = get_params_retrieve([*args])

        class_name = f'{cls.__name__}_{uuid4().hex}'
        newclass: Union[Serializer, ModelSerializer] = type(class_name, (cls,), {})

        declared_fields = cls._get_declared_fields(newclass)
        declared_fields_list = list(declared_fields.keys())
        meta_fields_list = cls._get_meta_fields(newclass)

        if meta_fields_list:
            cls._check_extra_fields(newclass, set(declared_fields_list+meta_fields_list), *first_level_fields)
            newclass.Meta.fields = first_level_fields
        else:
            cls._check_extra_fields(newclass, declared_fields_list, *first_level_fields)

        for field in declared_fields_list:
            if field not in first_level_fields:
                del declared_fields[field]

        if next_level_fields:
            cls._recursive_serializer_processing(declared_fields, next_level_fields)

        return newclass

    @classmethod
    def _get_meta_fields(cls, class_):
        if issubclass(class_, ModelSerializer) and hasattr(class_, 'Meta'):
            class_.Meta = type(f'Meta_{uuid4().hex}', cls.Meta.__bases__, dict(cls.Meta.__dict__))
            meta_fields_list = list(class_.Meta.fields)
            if class_.Meta.fields == ALL_FIELDS:
                raise ValueError(f'{ALL_FIELDS} does not support')
            return meta_fields_list

        return False

    @staticmethod
    def _get_declared_fields(class_):
        declared_fields = getattr(class_, '_declared_fields')
        return declared_fields

    @staticmethod
    def _check_extra_fields(class_, exist_fields, *args):
        extra_fields = [field_name for field_name in args if field_name not in exist_fields]
        if extra_fields:
            err_list = ', '.join(extra_fields)
            raise ValueError(f'{err_list} do not exist in Meta or declared_fields in {class_.__name__}')

    @staticmethod
    def _recursive_serializer_processing(declared_fields, next_level_fields):
        for key, val in next_level_fields.items():
            if isinstance(declared_fields[key], (Serializer, ModelSerializer)):
                serializer_kwargs = declared_fields[key].__dict__['_kwargs']
                declared_fields[key] = declared_fields[key].include_fields(*val)(**serializer_kwargs)

            if isinstance(declared_fields[key], RelatedField):
                nested_class_kwargs = declared_fields[key].__dict__['_kwargs']
                nested_class_kwargs['serializer_class'] = declared_fields[key].serializer_class.include_fields(*val)
                nested_class = declared_fields[key].__class__(**nested_class_kwargs)
                declared_fields[key] = nested_class

            # TODO for ManyRelatedField
            # if isinstance(declared_fields[key], ManyRelatedField):
            #     nested_class_kwargs = declared_fields[key].child_relation.__dict__['_kwargs']
            #     nested_ser = declared_fields[key].child_relation.serializer_class.include_fields(val)
            #     nested_class = declared_fields[key].child_relation.__class__(nested_ser, **nested_class_kwargs)
            #     declared_fields[key].child_relation = nested_class

    @property
    def fields(self):
        """
        Processing GET-params to include
        or exclude serializer fields
        Works only with first level!!!

        TODO recursive processing with GET-params to
        provide processing for 2nd Level, 3rd, ... levels)
        """
        fields = super().fields

        if not (hasattr(self, '_context') and 'request' in self.context.keys()):
            return fields

        request = self.context['request']
        if request and request.method == 'GET' and hasattr(request, 'query_params'):
            params = getattr(request, 'query_params')

            include_fields_raw = params.get('include_fields', None)
            exclude_fields_raw = params.get('exclude_fields', None)
            exist_fields = list(fields.keys())

            if (include_fields_raw, exclude_fields_raw) == (None, None):
                return fields

            if include_fields_raw is not None:
                include_fields = [f for f in include_fields_raw.split(',') if f in exist_fields]
                fields_to_pop_include = set(exist_fields) ^ set(include_fields)
            else:
                fields_to_pop_include = set()

            if exclude_fields_raw is not None:
                exclude_fields = [f for f in exclude_fields_raw.split(',') if f in exist_fields]
                fields_to_pop_exclude = set(exist_fields) & set(exclude_fields)
            else:
                fields_to_pop_exclude = set()

            if fields_to_pop_include and fields_to_pop_exclude:
                for key in min(fields_to_pop_include, fields_to_pop_exclude):
                    fields.pop(key)

            elif fields_to_pop_include or fields_to_pop_exclude:
                for key in max(fields_to_pop_include, fields_to_pop_exclude):
                    fields.pop(key)

        return fields
