from fastapi import APIRouter
from deps import SessionDep, PostDep
from sqlalchemy import select
from models import Post
from schemas import PostOut, PostCreate, PostUpdate

router = APIRouter(prefix='/api/posts')

@router.get('', response_model=list[PostOut])
def post_list(db: SessionDep):
    posts = db.scalars(select(Post).order_by(Post.created_at.desc())).all()

#for post in posts:
#    print(post.user.username)

    return posts

@router.get('/{post_id}', response_model=PostOut)
def post_detail(post: PostDep):
    #post = db.get(Post, post_id)
   # if post is None:
    #    raise HTTPException(status_code=404, detail='게시글을 찾을 수 없습니다')
    return post

@router.post('', response_model=PostOut, status_code=201)
def post_create(data: PostCreate, db: SessionDep):
    post = Post(content=data.content, user_id=data.user_id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

@router.patch('/{post_id}', response_model=PostOut)
def post_update(data: PostUpdate, post: PostDep, db: SessionDep):
    post.content = data.content
    db.commit()
    db.refresh(post)
    return post

@router.delete('/{post_id}', status_code=204)
def post_delete(post: PostDep, db: SessionDep):
    db.delete(post)
    db.commit()
