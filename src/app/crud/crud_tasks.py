from fastcrud import FastCRUD

from ..models.task import Task
from ..schemas.task import TaskCreateInternal, TaskDelete, TaskRead, TaskUpdate, TaskUpdateInternal

CRUDTasks = FastCRUD[Task, TaskCreateInternal, TaskUpdate, TaskUpdateInternal, TaskDelete, TaskRead]
crud_tasks = CRUDTasks(Task)
