### About
    FieldsManageMixin provides dynamic processing of serializer fields.
### Usage
    FieldsManageMixin provides dynamic processing of serializer fields
    via methods "exclude_fields" and "include_fields" directly from python 
    code or by GET-params from HTTP-requset
    
    Access by code:
    
    # serializers.py
    class MyFirstLevelSerializer(FieldsManageMixin, serializers.Serializer):
        first_field_1 = serializers.IntegerField()
        first_field_2 = serializers.CharField()
        first_field_3 = serializers.CharField()
        first_field_4 = MySecondLevelSerializer()
    
    class MySecondLevelSerializer(serializers.Serializer):
        second_field_1 = serializers.IntegerField()
        second_field_2 = serializers.CharField()
        second_field_3 = serializers.CharField()
        second_field_4 = serializers.CharField()
        
    class MyModelSerializer(FieldsManageMixin, serializers.ModelSerializer):
        
        class Meta:
            model = MyModel
            fields = ('model_field_1', 'model_field_2', 'model_field_3', 
                      'model_field_4', 'model_field_5', 'model_field_6',)
    ....
    
        
    # views.py
    class MyViewInclude(generics.GenericAPIView):
        serializer_class = MyFirstLevelSerializer.include_fields(
            'first_field_2','first_field_4{second_field_2;second_field_4}',
        )
        
    class MyViewExclude(generics.GenericAPIView):
        serializer_class = MyModelSerializer.exclude_fields(
            'model_field_3','model_field_6',
        )    
    ...
            
    Access by GET-params (works first level only):
        
    # views
    class MyView(generics.GenericAPIView):
        serializer_class = MyModelSerializer
        ....

   # access by url:
    127.0.0.1/v1/myapi?exclude_fields=model_field_3,model_field_6
   