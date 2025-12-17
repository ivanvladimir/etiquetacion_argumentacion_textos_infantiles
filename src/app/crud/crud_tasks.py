from fastcrud import FastCRUD

from ..models.task import Task
from ..schemas.task import TaskCreateInternal, TaskDelete, TaskRead, TaskUpdate, TaskUpdateInternal

CRUDPost = FastCRUD[Task, TaskCreateInternal, TaskUpdate, TaskUpdateInternal, TaskDelete, TaskRead]
crud_posts = CRUDPost(Task)
