class UserChunkedUpload(MPTTModel, AbstractChunkedUpload):
    """
    A model representing chunked uploads by users, with hierarchical relationships using MPTT.
    """

    class FileOrFolder(models.IntegerChoices):
        """
        Choices for distinguishing between files and folders.
        """

        FILE = 1
        FOLDER = 2

    # Existing fields
    objects = MyManager()
    filename = models.CharField(max_length=200)
    file_extension = models.CharField(max_length=20, blank=True, null=True, default="")
    file_classification = models.CharField(
        max_length=40, blank=True, null=True, default=""
    )
    file_or_folder = models.IntegerField(
        choices=FileOrFolder.choices, default=FileOrFolder.FILE
    )
    top_user_folder = models.BooleanField(
        blank=False, null=False, editable=False, default=False
    )
    human_size = models.CharField(max_length=20, default="-")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_chunked_uploads",
    )

    # New fields
    # Stores the path to the ingested version of the file.
    # To be updated after ingestion is completed
    ingested_file = models.FileField(blank=True, null=True)
    # Stores metadata about the ingestion process in JSON format.
    ingestion_metadata = models.JSONField(blank=True, null=True, default=dict)
    # Stores the path to the output file from data profiling.
    data_profiling_output = models.FileField(blank=True, null=True)

    class Meta:
        """
        Meta options for UserChunkedUpload.
        Includes database indexes for optimisation.
        """

        indexes = [models.Index(fields=["user", "parent", "status"])]

    def save(self, *args, **kwargs):
        """
        Override save method to add additional logic before saving the instance.
        """
        if self.offset:
            self.human_size = sizeof_fmt_decimal(self.offset)
            _, self.file_extension = os.path.splitext(self.filename)
        super(UserChunkedUpload, self).save(*args, **kwargs)

    @property
    def days_count(self):
        """Number of days since file uploaded"""
        if self.file_or_folder == 1 and self.status == 2:
            return (timezone.now() - self.completed_on).days
        else:
            return 0

    def __str__(self) -> str:
        """
        Property to calculate the number of days since the file was uploaded.
        """
        return self.filename



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