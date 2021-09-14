import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
import subprocess
import logging

logger = logging.getLogger('user_logger')
fh = logging.FileHandler('user.log')
fh.setLevel(logging.INFO)
logger.addHandler(fh)

class UserAgent(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)
        self.fileProbs = {'teamcore.usc.edu': 0.9, 'usc.edu': 0.7, 'google.com': 0.2}
        self.primitiveActions([('isNeeded', self.isNeeded), ('download', self.download)])

        self.readAgent("""

goalWeight doWork 1


goalRequirements doWork
  readFile('teamcore.usc.edu')
  readFile('usc.edu')
  readFile('google.com')
  sleep(1)
  forget([readFile(x),isNeeded(x),download(x),sleep(x)])  # a built-in that removes matching elements from memory


goalRequirements readFile(file)
  isNeeded(file)
  download(file)

# Succeed if you failed to actually read the file
# so the agent goes on to try the others
goalRequirements readFile(file)


transient doWork     # Agent will forget goal's achievement or failure as soon as it happens

""")

    def isNeeded(self, f):
        f = f[1][1:]
        #    print('isneeded: ' + f)
        import random
        r = random.random()
        print(r)
        if r <= self.fileProbs[f]:
            return [{}]
        else:
            return []

    def download(self, f):
        f = f[1][1:]
        print('downloading: ' + f)
        proc = subprocess.Popen(['wget', f],shell=True, stdout=subprocess.PIPE, stderr = subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if 'saved' in stderr or 'command not found' in stderr:
            logger.warning('Download ' + f + ' succeeded')
            print(stderr)
            return[{}]
        elif 'failed' in stderr:
            logger.warning('Download ' + f + ' failed')
            return[]
        else:
            raise Exception("unknown output: " + str(stderr))


if __name__ == "__main__":
    UserAgent().agent_loop()

