from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import JSONField

# Create your models here.

#User 테이블
class UserProfile(AbstractUser):
    user_image = models.CharField(max_length=255, verbose_name="유저 프로필 이미지")
    user_position = models.CharField(max_length=255, verbose_name="유저가 속한 그룹", null=True)
    user_info = models.CharField(max_length=255, verbose_name="유저가 작성한 프로필 설명", null=True)
    user_hash = models.CharField(max_length=255, verbose_name="해시태그", null=True)
    success_count = models.IntegerField(verbose_name="만다라트 실천 횟수", default=0)
    provider = models.CharField(max_length=50, verbose_name="가입 방법", default="EMAIL")
    created_at = models.DateTimeField(auto_now_add=True, null=True)  # 가입한 일시
    updated_at = models.DateTimeField(auto_now=True, null=True)  # 프로필 정보 업데이트 일시
    deleted_at = models.DateTimeField(null=True) # 탈퇴한 일시

    REQUIRED_FIELDS = ['email']

#Follow 테이블
class Follow(models.Model):
    followed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='follower', db_index=True)
    following_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following', verbose_name="내가 팔로우 한 사람", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

#핵심목표
class MandaMain(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # 외래키로 User 모델 연결
    success = models.BooleanField(default=False)  # 성공 여부 (True/False)
    main_title = models.CharField(max_length=100)  # 메인 타이틀, 필요에 따라 길이 조절 가능
    created_at = models.DateTimeField(auto_now_add=True, null=True)  # 만다라트 생성일시
    deleted_at = models.DateTimeField(null=True)  # 만다라트 삭제일시

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.main_title
    
    def save(self, *args, **kwargs):
        super(MandaMain, self).save(*args, **kwargs)

        # MandaSub 객체 생성
        for _ in range(8):
            MandaSub.objects.create(main_id=self)

        # MandaContent 객체 생성
        sub_instances = MandaSub.objects.filter(main_id=self)
        for sub_instance in sub_instances:
            for _ in range(8):
                MandaContent.objects.create(sub_id=sub_instance)

#세부목표
class MandaSub(models.Model):
    main_id = models.ForeignKey(MandaMain, on_delete=models.CASCADE)  # MandaMain 모델과 외래키로 연결
    success_count = models.IntegerField(default=0)  # 성공 여부, bigint 타입
    sub_title = models.CharField(max_length=100, null=True)  # 서브 타이틀, 최대 길이 50

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.sub_title

#실천목표
class MandaContent(models.Model):
    sub_id = models.ForeignKey(MandaSub, on_delete=models.CASCADE)  # 외래키로 MandaSub와 연결
    success_count = models.IntegerField(default=0)  # 성공 여부, bigint 타입
    content = models.CharField(max_length=100, null=True)  # 콘텐츠, 최대 길이 50

    class Meta:
        ordering = ['id']
        
    def __str__(self):
        return self.content
    
#Feed 테이블
class Feed(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # user_id 외래 키
    cont_id = models.ForeignKey(MandaContent, on_delete=models.CASCADE)  # cont_id 외래 키
    main_id = models.ForeignKey(MandaMain, on_delete=models.CASCADE)  # main_id 외래 키
    sub_id = models.ForeignKey(MandaSub, on_delete=models.CASCADE)  # sub_id 외래 키
    feed_contents = models.TextField()  # 피드 내용
    feed_image = models.ImageField(upload_to='feed_images/')  # 이미지를 저장할 경로
    created_at = models.DateTimeField(auto_now_add=True)  # 피드 생성일
    updated_at = models.DateTimeField(auto_now=True)  # 피드 업데이트일
    deleted_at = models.DateTimeField(null=True)  # 피드 삭제일시
    feed_hash = models.CharField(max_length=255)  # 피드 해시값, 필요에 따라 길이 조절 가능
    emoji_count = JSONField(blank=True, null=True, default=dict)

    def __str__(self):
        return self.feed_contents

#댓글
class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, db_index=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)  # 댓글 삭제일시

#반응(이모지, 좋아요 기능)
class Reaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, db_index=True)
    emoji_name = models.CharField(max_length=50)

#알람(댓글, 좋아요, 팔로우)
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('follow', 'Follow'),
        ('comment', 'Comment'),
        ('reaction', 'Reaction'),
    )

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_notifications')
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, null=True)
    comment = models.TextField(null=True)
    total_count = models.IntegerField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
class ChatRoom(models.Model):
    room_number = models.AutoField(primary_key=True)
    starter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='started_chats')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_chats', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    latest_message_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'ChatRoom: {self.starter.username} and {self.receiver.username}'

class ChatMessage(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'Message: {self.author.username} at {self.created_at}'

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.chatroom.latest_message_time = self.created_at
        self.chatroom.save()

from django.db import models
from django.conf import settings
from django.utils import timezone

class BlockedUser(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocking_users')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_users')
    blocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocks {self.blocked.username}"

class ReportedFeed(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_posts')
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='reported_by_users')
    reason = models.CharField(max_length=255, blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reporter', 'feed')

    def __str__(self):
        return f"Feed {self.feed.id} reported by {self.user.username}"
    
class ReportedComment(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_comments')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reported_by_users')
    reason = models.CharField(max_length=255, blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reporter', 'comment')

    def __str__(self):
        return f"Feed {self.comment.id} reported by {self.user.username}"