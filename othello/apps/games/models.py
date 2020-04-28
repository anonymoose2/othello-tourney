import os
import uuid

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField

from .storage import OverwriteStorage
from ...moderator.moderator import Player


PLAYER_CHOICES = (
    (Player.BLACK.value, 'Black'),
    (Player.WHITE.value, "White"),
)


def save_path(instance, filename):
    return os.path.join(instance.user.short_name, f"{uuid.uuid4()}.py")


class SubmissionSet(models.QuerySet):

    def usable(self, user=None):
        return self.filter(user=user, usable=True) if user else self.filter(usable=True)


class Submission(models.Model):

    objects = SubmissionSet.as_manager()

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
    name = models.CharField(max_length=500, default="")
    submitted_time = models.DateTimeField(auto_now=True)
    code = models.FileField(
        upload_to=save_path,
        storage=OverwriteStorage(),
        default=None,
    )
    usable = models.BooleanField(default=True)

    def get_name(self):
        return self.name

    def get_user_name(self):
        return self.user.short_name

    def get_submitted_time(self):
        return self.submitted_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_submission_name(self):
        return f'{self.get_name()}: <{self.get_submitted_time()}>'

    def get_code_filename(self):
        return self.code.name

    @property
    def is_usable(self):
        return self.usable

    def set_usable(self):
        for x in Submission.objects.filter(user=self.user):
            if x != self:
                x.usable = False
            else:
                x.usable = True
            x.save()

    def save(self, *args, **kwargs):
        if self.usable:
            for x in Submission.objects.filter(user=self.user):
                if x != self:
                    x.usable = False
                    x.save()
        super(Submission, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.code.storage.delete(self.code.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.get_user_name()}: {self.get_submission_name()}"


class GameSet(models.QuerySet):

    def running(self):
        return self.filter(playing=True)


class Game(models.Model):

    OUTCOME_CHOICES = (
        (Player.BLACK.value, "Black"),
        (Player.WHITE.value, "White"),
        ('T', "Tie")
    )

    objects = GameSet.as_manager()

    black = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="black")
    white = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="white")
    time_limit = models.IntegerField(default=5,)
    playing = models.BooleanField(default=False)

    forfeit = models.BooleanField(default=False)
    outcome = models.CharField(max_length=1, choices=OUTCOME_CHOICES, default='')

    @property
    def channels_group_name(self):
        return f"game-{self.id}"

    def __str__(self):
        return f"{self.black.user} (Black) vs {self.white.user} (White) [{self.time_limit}s]"


class MoveSet(models.QuerySet):

    def latest(self):
        return self.order_by('-created_at')[0] if self.exists() else None


class Move(models.Model):

    manager = MoveSet.as_manager()

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moves")
    created_at = models.DateTimeField(auto_now_add=True)
    board = models.CharField(max_length=64, default='')
    player = models.CharField(max_length=1, choices=PLAYER_CHOICES)
    move = models.IntegerField(default=-10)

    flipped = ArrayField(models.IntegerField(default=-1), default=list)
    possible = ArrayField(models.IntegerField(default=-1), default=list)

    def __str__(self):
        return f"{self.game}, {self.player}, {self.move}, {self.created_at}"


class GameObjectSet(models.QuerySet):

    def latest(self):
        return self.order_by('-created_at')[0] if self.exists() else None


class GameObject(models.Model):

    manager = GameObjectSet.as_manager()

    created_at = models.DateTimeField(auto_now_add=True)
    player = models.CharField(max_length=1, choices=PLAYER_CHOICES)

    class Meta:
        abstract = True


class GameError(GameObject):

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="errors")
    error_code = models.IntegerField(default=-1)
    error_msg = models.CharField(max_length=10*1024, default="")


class GameLog(GameObject):

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="logs")
    message = models.CharField(max_length=10*1024, default="")