import ray
from ray import workflow
from collections import defaultdict

class WorkflowTree:
    def __init__(
        self, 
        workflow_data: dict, 
        tasks_data: dict
    ):
        """
        Tree structure for building a tree on the frontend. 
        This class organized the data to be easily accessed by
        the dashboard manager.

        Args: 
        
        Dict workflow_metadata: {
            workflow_id,
            status,
            user_metadata,
            stats,
        }
        Dict task_data: {
            "downstream_dependencies": list,
            "task_execution_data": obj,
            "task_data": obj
        }
        
        """
        #workflow data
        self._status = workflow_data["status"]
        self._workflow_user_metatdata = workflow_data["user_metatdata"]
        self._id = workflow_data["workflow_id"]
        self._stats = workflow_data["stats"]

        #tasks(NODES) data (for this workflow)
        self._dependencies = tasks_data["downstream_dependencies"]

        #self._edges is in the form [(t1, t2), (t2, t3), ect.]
        self._edges = defaultdict(list)
        for task1, dependencies in self._dependencies:
            for task2 in dependencies: 
                self._edges.append((task1, task2))

        # a dictionary {task_id: Task(data)}
        self._nodes = tasks_data["task_data"]

        # dictionary of run_time data
        self._exec_data = tasks_data["task_execution_data"]

    def __repr__():
        pass
    
    def getNodes(self):
        return self._nodes
    
    def getEdges(self):
        return self._edges

