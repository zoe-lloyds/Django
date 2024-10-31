class UserChunkedUploadSerialiser(serializers.ModelSerializer):
    """
    Serialiser for UserChunkedUpload model.
    Provides custom serialisation for completed_on and days_count fields.
    """

    completed_on = serializers.SerializerMethodField()
    days_count = serializers.ReadOnlyField()

    class Meta:
        """
        Meta options for UserChunkedUploadSerialiser.
        Specifies the model and the fields to include in the serialisation.
        """

        model = UserChunkedUpload
        # exclude = ["file"]
        fields = [
            "id",
            "file",
            "filename",
            "file_or_folder",
            "file_extension",
            "completed_on",
            "parent",
            "human_size",
            "days_count",
            "offset",
        ]

    def get_completed_on(self, obj):
        """
        Custom method to get the completed_on field.
        Returns a formatted date if the file_or_folder is a file and the status is completed.
        """
        if obj.file_or_folder == 1 and obj.status == 2:
            return DateFormat(obj.completed_on).format("j M Y, P")