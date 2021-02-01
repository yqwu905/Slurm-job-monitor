import json


class jobs():
    def __init__(self, filename):
        self.job_list = list()
        self.filename = filename

    # 函数说明:加载任务数据
    # 参数:filename:储存任务数据的json文件;
    # 返回值：任务数据
    def load_job_list(self):
        with open(self.filename, 'r') as fp:
            self.job_list = json.load(fp)

    #
    def add_job(self, id, server, user, work_dir, status):
        self.job_list.append({"id": id,
                              "server": server,
                              "user": user,
                              "work_dir": work_dir,
                              "status": status})
        with open(self.filename, 'w') as fp:
            json.dump(self.job_list, fp)

    #
    def update_job_status(self, id, status):
        for i in self.job_list:
            if i['id'] == id:
                i['status'] = status
                break
        with open(self.filename, 'w') as fp:
            json.dump(self.job_list, fp)

    #
    def query_job_info(self, id):
        for i in self.job_list:
            if i['id'] == id:
                return i
