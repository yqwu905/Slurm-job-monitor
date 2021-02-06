import json


class jobs():
    def __init__(self, filename='./job_list.json'):
        self.job_list = list()
        self.filename = filename
        with open(self.filename, 'r') as fp:
            self.job_list = json.load(fp)

    #
    def add_job(self, job_id, server, user, work_dir, local, status):
        self.job_list.append({"job_id": job_id,
                              "server": server,
                              "user": user,
                              "work_dir": work_dir,
                              "local": local,
                              "status": status})
        with open(self.filename, 'w') as fp:
            json.dump(self.job_list, fp)

    #
    def update_job_status(self, job_id, status):
        for i in self.job_list:
            if i['id'] == job_id:
                i['status'] = status
                break
        with open(self.filename, 'w') as fp:
            json.dump(self.job_list, fp)

    #
    def query_job_info(self, job_id):
        for i in self.job_list:
            if i['job_id'] == job_id:
                return i
