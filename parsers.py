from pydriller.repository import MalformedUrl
from pydriller import Repository
from utils import _clone_remote_repo
from git import cmd
import logging
import re
import os

# overwrite _clone_remote_repo of pydriller.repository class
# to support 'progress' param in underlying Repo.clone_from
# function call
Repository._clone_remote_repo = _clone_remote_repo


class GitRepository:
    def __init__(self, repo_params: dict):
        """
         wrapper around pydriller.repository class.
         this is a base class and not to be called as a parser
        :param repo_params: repo_params dictionary
        """
        self.log = logging.getLogger(self.__class__.__name__)

        self.repo_params = repo_params
        self.repo_path = self.repo_params.get("path_to_repo")
        self.repo_name = Repository._get_repo_name_from_url(
            self.repo_path)

        self.cache_dir_path = self.repo_params.get("clone_repo_to")
        if self.cache_dir_path:
            self.create_cache_path(self.cache_dir_path)
            self.update_cache_repo(self.cache_dir_path)

        self.commits = self.get_commits()
        self.callback()

    def callback(self):
        # callback function to show updates of commits
        self.log.info(f"fetched {len(self.commits)} commits for "
                      f"repository {self.repo_path}")

    def get_commits(self):
        self.log.info(f"fetching commits for repository {self.repo_path}")
        repository = Repository(**self.repo_params)
        return list(repository.traverse_commits())

    def create_cache_path(self, dir_path):
        # cache folder needs to be created in advance
        if not os.path.exists(dir_path):
            # repo directory will be created when get_commits is called
            self.log.info(f"creating cache directory {dir_path}")
            os.makedirs(dir_path)

    def update_cache_repo(self, dir_path):
        # run git pull on cached repository folder
        cache_repo_path = os.path.join(dir_path, self.repo_name)
        if os.path.exists(cache_repo_path):
            repo = cmd.Git(cache_repo_path)
            self.log.info(f"pulling changes for repository {self.repo_path}"
                          f" (cache path: {cache_repo_path})")
            repo.pull()


class GitRepositoryParser(GitRepository):
    def __init__(self, repo_params: dict, parser_params: dict):
        """
        child class of GitRepository to provide additional functionality
        that pydriller.repository class does not provide by default
        :param repo_params: repo_params dictionary
        :param parser_params: parser_params dictionary
        """
        super().__init__(repo_params)

        if not Repository._is_remote(self.repo_path):
            # get remote url of local repository
            self.git_repo = cmd.Git(self.repo_path)
            self.repo_url = self.git_repo.execute(
                "git config --get remote.origin.url",
                shell=True)
        else:
            # remote repository so url was already provided
            self.repo_url = self.repo_path

        self.git_org = self.get_org_from_repo_url(self.repo_url)
        self.git_url = self.get_git_url_from_repo(self.repo_url)
        self.parser_params = parser_params

        if self.parser_params:
            self.exclude_authors()

    def get_org_from_repo_url(self, url: str):
        # return any word preceding /repo_name in url
        match = re.search(rf"\w+(?=/{self.repo_name})", url)
        if not match:
            raise MalformedUrl(f"unable to parse organization"
                               f" from url {self.repo_path}")
        else:
            self.log.debug(f"git organization: {match.group()}")
            return match.group()

    def get_git_url_from_repo(self, url: str):
        # return any word between https://|http://|git@ and .com
        match = re.search(r"(https://|http://|git@)(\w+.com)", url)
        if not match:
            raise MalformedUrl(f"unable to parse git domain"
                               f" from url {self.repo_path}")
        else:
            self.log.debug(f"git domain: {match.group(2)}")
            return match.group(2)

    def exclude_authors(self):
        # exclude commit messages based on the
        # provided list of excluded authors
        if "exclude_authors" in self.parser_params:
            authors = self.parser_params.get("exclude_authors")

            if authors:
                self.log.info(f"filtering commits based on excluded "
                              f"authors {authors}")
                commits = [commit for commit in self.commits
                           if commit.author.name not in authors]
                self.commits = commits
                self.callback()


class GitRepoCommitPretty(GitRepositoryParser):
    def __init__(self, repo_params: dict, parser_params: dict):
        """
        child class of GitRepositoryParser to provide
        pretty print functionality
        :param repo_params: repo_params dictionary
        :param parser_params: parser_params dictionary
        """
        super().__init__(repo_params, parser_params)

        self.commit_data = [{"msg": commit.msg.split("\n")[0],  # get the fist line in the commit
                             "sha": commit.hash}
                            for commit in self.commits]

        self.expand_jira_project_refs()
        self.expand_pull_request_refs()
        self.generate_commit_url_refs()

        self.pretty_print()

    def expand_jira_project_refs(self):
        # expand user references to jira projects
        jira_project_refs = self.parser_params.get("expand_jira_project_refs")
        if jira_project_refs and jira_project_refs.get("enabled"):

            jira_project_keys = jira_project_refs.get("keys_to_expand")
            if jira_project_keys:
                self.log.info(f"expanding jira project references")

                project_keys = "|".join(jira_project_keys)
                re_pattern = re.compile(r"""
                   ([\W]?     # any optional character 
                   (({})-\d+) # group of jira keys followed by dash and numbers
                   [\W]?)     # any optional character 
                """.format(project_keys), re.VERBOSE | re.IGNORECASE)
                re_replace = r"https://sentinelone.atlassian.net/browse/\2 "
                # update self.commit_data list of dictionaries
                for commit in self.commit_data:
                    message = re.sub(re_pattern, re_replace,
                                     commit["msg"])
                    commit.update({"msg": message})

    def expand_pull_request_refs(self):
        # expand git references to pull requests
        if self.parser_params.get("expand_pull_request_refs"):
            self.log.info(f"expanding pull request references")

            re_pattern = re.compile(r"""
                ([\W]?  # any optional character
                \#(\d+) # #(numbers) pattern
                [\W]?)  # any optional character
            """, re.VERBOSE)
            # dynamically generate url of a type
            # https://<git_domain>/org/repo/pull/number
            re_replace = rf" https://{self.git_url}/{self.git_org}/" \
                         rf"{self.repo_name}/pull/\2 "
            # update self.commit_data list of dictionaries
            for commit in self.commit_data:
                message = re.sub(re_pattern, re_replace,
                                 commit["msg"])
                commit.update({"msg": message})

    def generate_commit_url_refs(self):
        # append url reference to a commit
        if self.parser_params.get("generate_commit_url_refs"):
            self.log.info(f"generating commit url references")

            for commit in self.commit_data:
                # dynamically generate url of a type
                # https://<git_domain>/org/repo/commit/commit_sha
                commit_url = f"https://{self.git_url}/{self.git_org}/" \
                             f"{self.repo_name}/commit/{commit['sha']}"
                # update self.commit_data list of dictionaries
                message = commit["msg"] + " - " + commit_url
                commit.update({"msg": message})

    def pretty_print(self):
        # pretty print self.commit_data
        self.log.info(f"generating pretty print")
        commit_data = [commit["msg"] for commit in self.commit_data]

        print(f"\nlist of commits to repository {self.repo_path} "
              f"from commit {self.repo_params.get('from_commit')} "
              f"to commit {self.repo_params.get('to_commit')}:")

        for num, commit in enumerate(commit_data, 1):
            print(f"{num}.", commit)

        print("\n")
