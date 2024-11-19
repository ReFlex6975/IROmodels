from django.contrib.auth import get_user_model
from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser


from pydantic import ValidationError

CustomUser = get_user_model()


# Пользователь
class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    date_of_birth = models.DateField(null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    school = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=100, choices=[
        ('region_1', 'Регион 1'),
        ('region_2', 'Регион 2'),
        ('region_3', 'Регион 3'),
        ('region_4', 'Регион 4'),
    ], null=True, blank=True)
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User')
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.email


# Конкурс
class Contest(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    description = models.TextField(verbose_name="Описание")
    status = models.IntegerField(
        choices=[(1, 'Скоро начнется'), (2, 'Идет конкурс'), (3, 'Архив')],
        null=True,
        blank=True
    )
    moderators = models.ManyToManyField(
        CustomUser,
        related_name='moderator_contests',
        blank=True,
        verbose_name="Модераторы"
    )
    experts = models.ManyToManyField(
        CustomUser,
        related_name='expert_contests',
        blank=True,
        verbose_name="Эксперты"
    )

    def __str__(self):
        return self.title

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Дата начала не может быть позже даты окончания.")


# Этап конкурса
class Stage(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="stages")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(editable=False)  # Автоматический порядок этапов
    start_date = models.DateField()
    end_date = models.DateField()

    def save(self, *args, **kwargs):
        # Автоматический порядок этапов
        if not self.pk:
            self.order = (self.contest.stages.count() + 1)
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Дата начала не может быть позже даты окончания.")

    def __str__(self):
        return f"{self.title} (Этап {self.order})"


# Критерий оценки
class Criterion(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="criteria")
    name = models.CharField(max_length=255)
    max_points = models.IntegerField()

    def __str__(self):
        return self.name


# Работа участника
class Submission(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='submissions/')
    submission_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if now().date() > self.stage.end_date:
            raise ValidationError("Работа должна быть подана до конца текущего этапа.")

    def __str__(self):
        return self.title


# Участник конкурса
class ContestParticipant(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'contest')

    def __str__(self):
        return f"{self.user.email} - {self.contest.title}"


# Оценка работы
class Evaluation(models.Model):
    expert = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'user'})
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE)
    points = models.IntegerField()

    def clean(self):
        if self.points > self.criterion.max_points:
            raise ValidationError("Баллы не могут превышать максимального значения критерия.")

    class Meta:
        unique_together = ('expert', 'submission', 'criterion')

    def __str__(self):
        return f"Оценка {self.points} за {self.submission.title}"


# Награды и результаты конкурса
class Award(models.Model):
    participant = models.ForeignKey(ContestParticipant, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    place = models.PositiveIntegerField()
    award_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.participant.user.email} - {self.place} место ({self.contest.title})"
