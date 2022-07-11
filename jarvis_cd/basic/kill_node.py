
from jarvis_cd.node import Node
from jarvis_cd.basic.exec_node import ExecNode
from jarvis_cd.basic.node_exec_node import NodeExecNode
import re

class KillNode(NodeExecNode):
    def __init__(self, program_regex, **kwargs):
        if not isinstance(program_regex, list):
            program_regex = [program_regex]
        self.program_regex = program_regex
        self.kwargs = kwargs
        super().__init__(**kwargs)

    def _LocalRun(self):
        node = ExecNode('ps -ef', print_output=False).Run()
        pids = []
        for line in node.output[0]['localhost']['stdout']:
            words = line.split()
            if len(words) <= 7:
                continue
            #Split the command into tokens and check if each token matches a regex
            cmd = words[7:]
            cmd_matches = all([re.match(regex, cmd_token) is not None for regex,cmd_token in zip(self.program_regex,cmd)])
            if cmd_matches:
                pids.append(int(words[1]))
        if len(pids) > 0:
            for pid in pids:
                ExecNode(f"kill -9 {pid}", sudo=True).Run()
                self.output[0]['localhost']['stdout'].append(f"Killing {pid}")
        else:
            self.output[0]['localhost']['stdout'].append(f"No PIDs to kill")
