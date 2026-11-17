import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def login(username, password):
  res = client.post(
    '/api/auth/login',
    data={'username': username, 'password': password}
  )
  token = res.json()['access_token']

  return {'Authorization': f'Bearer {token}'}


def my_id(headers):
  # 지금 로그인한 사람의 id를 알아낸다
  return client.get('/api/auth/me', headers=headers).json()['id']


@pytest.fixture
def post():
  # 테스트마다 alice가 새 글을 하나 쓰고, 테스트가 끝나면(성공이든 실패든) 그 글을 지운다.
  # 글을 지우면 그 글에 달린 댓글과 하트도 같이 지워진다. (models.py의 cascade 설정)
  alice = login('alice', 'pw1234')
  res = client.post('/api/posts', json={'content': '댓글/하트 테스트용 글'}, headers=alice)
  assert res.status_code == 201
  post_id = res.json()['id']

  yield post_id

  client.delete(f'/api/posts/{post_id}', headers=alice)


def write_comment(post_id, headers, content='테스트 댓글'):
  res = client.post(f'/api/posts/{post_id}/comments', json={'content': content}, headers=headers)
  return res


def comment_ids(post_id):
  # 그 글의 댓글 목록에 있는 댓글 id들
  res = client.get(f'/api/posts/{post_id}/comments')
  return [c['id'] for c in res.json()]


def liked_user_ids(post_id):
  # 그 글에 하트를 누른 사람 id들
  res = client.get(f'/api/posts/{post_id}')
  return [like['user_id'] for like in res.json()['likes']]


# ---------- 댓글 ----------

# 1. 댓글을 쓰면 201이고, 그 글의 댓글 목록에 보인다
def test_comment_create_201_and_in_list(post):
  bob = login('bob', 'pw1234')

  res = write_comment(post, bob, '첫 댓글')
  assert res.status_code == 201
  assert res.json()['content'] == '첫 댓글'
  assert res.json()['user']['username'] == 'bob'

  assert res.json()['id'] in comment_ids(post)


# 2. 내 댓글을 고치면 200이고, 내용이 바뀐다
def test_comment_update_200(post):
  bob = login('bob', 'pw1234')
  comment_id = write_comment(post, bob, '고치기 전').json()['id']

  res = client.patch(f'/api/comments/{comment_id}', json={'content': '고친 후'}, headers=bob)
  assert res.status_code == 200
  assert res.json()['content'] == '고친 후'

  # 목록에서 다시 봐도 바뀌어 있어야 한다
  comments = client.get(f'/api/posts/{post}/comments').json()
  saved = [c for c in comments if c['id'] == comment_id][0]
  assert saved['content'] == '고친 후'


# 3. 남의 댓글을 고치거나(PATCH) 지우면(DELETE) 403
def test_other_users_comment_patch_delete_403(post):
  bob = login('bob', 'pw1234')
  carol = login('carol', 'pw1234')
  comment_id = write_comment(post, bob, 'bob의 댓글').json()['id']

  res = client.patch(f'/api/comments/{comment_id}', json={'content': 'carol이 고침'}, headers=carol)
  assert res.status_code == 403

  res = client.delete(f'/api/comments/{comment_id}', headers=carol)
  assert res.status_code == 403

  # 댓글은 그대로 남아 있어야 한다
  assert comment_id in comment_ids(post)


# 4. 없는 댓글을 고치면 404
def test_comment_update_not_found_404():
  bob = login('bob', 'pw1234')

  res = client.patch('/api/comments/9999999', json={'content': '없는 댓글'}, headers=bob)
  assert res.status_code == 404


# 5. 내 댓글을 지우면 204이고, 목록에서 사라진다
def test_comment_delete_204_and_gone(post):
  bob = login('bob', 'pw1234')
  comment_id = write_comment(post, bob, '지울 댓글').json()['id']

  res = client.delete(f'/api/comments/{comment_id}', headers=bob)
  assert res.status_code == 204

  assert comment_id not in comment_ids(post)


# ---------- 하트(좋아요) ----------

# 6. 하트를 누르면 201이고, 글의 likes에 내가 있다
def test_like_create_201(post):
  bob = login('bob', 'pw1234')

  res = client.post(f'/api/posts/{post}/likes', headers=bob)
  assert res.status_code == 201

  assert my_id(bob) in liked_user_ids(post)


# 7. 이미 누른 하트를 또 누르면 409
def test_like_twice_409(post):
  bob = login('bob', 'pw1234')

  client.post(f'/api/posts/{post}/likes', headers=bob)
  res = client.post(f'/api/posts/{post}/likes', headers=bob)
  assert res.status_code == 409


# 8. 하트를 취소하면 200이고, likes에서 내가 빠진다
def test_like_delete_200(post):
  bob = login('bob', 'pw1234')
  client.post(f'/api/posts/{post}/likes', headers=bob)

  res = client.delete(f'/api/posts/{post}/likes', headers=bob)
  assert res.status_code == 200

  assert my_id(bob) not in liked_user_ids(post)
