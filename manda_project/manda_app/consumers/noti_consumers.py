from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from datetime import datetime
from ..models import Feed, Notification, UserProfile, Comment

class FollowConsumer(AsyncWebsocketConsumer):
    
    # 클라이언트로부터 웹소켓 연결
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_authenticated:
            self.room_group_name = f"notifications_{self.user.id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    # 클라이언트로부터 웹소켓 연결 끊어짐
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            
    # 클라이언트로부터 메시지 수신
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # 팔로우 이벤트
        if text_data_json['type'] == 'follow_event':
            followed_user_id = text_data_json["followed_user_id"]
            user_id = text_data_json["user_id"]
            username = text_data_json["username"]
            user_image = text_data_json["user_image"]
            created_at = datetime.now().isoformat()
            user_profile = await self.get_user_profile(user_id)
            followed_user = await self.get_user_profile(followed_user_id)

            noti_id = await self.save_notification(
                sender=user_profile,
                recipient=followed_user, 
                notification_type='follow',
            )

            await self.channel_layer.group_send(
                f"notifications_{followed_user_id}", {
                    "type": "follow",
                    "user_id": user_id,
                    "username": username,
                    "user_image": user_image,
                    "created_at": created_at,
                    "noti_id": noti_id
                }
            )

        # 댓글 이벤트
        if text_data_json['type'] == 'comment_event':
            user_id = text_data_json["user_id"]
            username = text_data_json["username"]
            user_image = text_data_json["user_image"]
            comment = text_data_json["comment"]
            created_at = datetime.now().isoformat()
            user_profile = await self.get_user_profile(user_id)

            feed_id = text_data_json["feed_id"]
            feed = await self.get_feed(feed_id)
            
            if feed:
              feed_owner = await self.get_feed_user(feed)

              noti_id = await self.save_notification(
                  notification_type='comment',
                  sender=user_profile,
                  recipient=feed_owner,
                  comment=comment,
                  feed=feed
              )

              await self.channel_layer.group_send(
                  f"notifications_{feed_owner.id}", {
                      "type": "comment",
                      "user_id": user_id,
                      "feed_id": feed_id,
                      "username": username,
                      "comment": comment,
                      "user_image": user_image,
                      "created_at": created_at,
                      "noti_id": noti_id
                  }
              )

        # 리액션 이벤트
        if text_data_json['type'] == 'reaction_event':
            user_id = text_data_json["user_id"]
            username = text_data_json["username"]
            user_image = text_data_json["user_image"]
            total_count = text_data_json["total_count"]
            created_at = datetime.now().isoformat()
            user_profile = await self.get_user_profile(user_id)

            feed_id = text_data_json["feed_id"]
            feed = await self.get_feed(feed_id)
            
            if feed:
              feed_owner = await self.get_feed_user(feed)
              
              if total_count % 10 != 0:
                  return
              
              noti_id = await self.save_notification(
                  notification_type='reaction',
                  sender=user_profile,
                  recipient=feed_owner,
                  total_count=total_count,
                  feed=feed
              )

              if (total_count <= 100 and total_count % 10 == 0) or \
                (100 < total_count <= 1000 and total_count % 100 == 0) or \
                (1000 < total_count <= 10000 and total_count % 1000 == 0) or \
                (total_count > 10000 and total_count % 10000 == 0):
                  
                  await self.channel_layer.group_send(
                      f"notifications_{feed_owner.id}", {
                          "type": "reaction",
                          "user_id": user_id,
                          "feed_id": feed_id,
                          "username": username,
                          "total_count": total_count,
                          "user_image": user_image,
                          "created_at": created_at,
                          "noti_id": noti_id
                      }
                  )

    # 클라이언트에 팔로우 알림 전송
    async def follow(self, event):
        await self.send(text_data=json.dumps({
            'type': 'follow',
            "user_id": event["user_id"],
            "username": event["username"],
            "user_image": event["user_image"],
            "created_at": event["created_at"],
            "noti_id": event["noti_id"],
            "is_read": False
        }))

    # 클라이언트에 댓글 알림 전송
    async def comment(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment',
            "user_id": event["user_id"],
            "feed_id": event["feed_id"],
            "username": event["username"],
            "comment": event["comment"],
            "user_image": event["user_image"],
            "created_at": event["created_at"],
            "noti_id": event["noti_id"],
            "is_read": False
        }))

    # 클라이언트에 리액션 알림 전송
    async def reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            "user_id": event["user_id"],
            "feed_id": event["feed_id"],
            "username": event["username"],
            "total_count": event["total_count"],
            "user_image": event["user_image"],
            "created_at": event["created_at"],
            "noti_id": event["noti_id"],
            "is_read": False
        }))

    # 피드 객체 가져오기
    @database_sync_to_async
    def get_feed(self, feed_id):
        feed = Feed.objects.get(id=feed_id)
        return feed
    
    # 피드 유저 객체 가져오기
    @database_sync_to_async
    def get_feed_user(self, feed):
        return feed.user
    
    # 유저 프로필 객체 가져오기
    @database_sync_to_async
    def get_user_profile(self, user_id):
        user_profile = UserProfile.objects.get(id=user_id)
        return user_profile
  
    # DB에 알림 히스토리 저장
    @database_sync_to_async
    def save_notification(self, sender, recipient, notification_type, feed=None, comment=None, total_count=None):
        notification = Notification.objects.create(
            sender=sender,
            recipient=recipient,
            notification_type=notification_type,
            feed=feed if feed else None,
            comment=comment if notification_type == 'comment' else None,
            total_count=total_count if notification_type == 'reaction' else None,
        )
        return notification.id if notification else None