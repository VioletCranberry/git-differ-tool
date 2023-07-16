## Git Differ Tool

Extendable framework built around [PyDriller](https://github.com/ishepard/pydriller) to easily extract information 
about commits in multiple Git repositories with the following functionality added:

1. keeping cached repositories up-to-date on subsequent runs (if `clone_repo_to` is supplied to `repository_params` - see configuration below)
2. extension of JIRA references in commit messages (based on provided Jira project keys)
3. extension of GitHub Pull Request references in commit messages
4. generation of GitHub commit URLs

Example for a single GIT repository:

```
list of commits to repository git@github.com:kubernetes/kubernetes.git from commit 5c96e53 to commit 900237f:
1. Implement KEP-3836 - https://github.com/kubernetes/kubernetes/commit/9b1c4c7b57f7fbdd776f5103c89ed1f461c295d0
2. Implement metrics agreed on the KEP - https://github.com/kubernetes/kubernetes/commit/08dd657a71c07cf5e71e1b191fd9e8588786b3db
3. kubelet: devices: skip allocation for running pods - https://github.com/kubernetes/kubernetes/commit/3bcf4220ece998d626ae670f911f8a1a1bb31507
4. e2e: node: devicemanager: update tests - https://github.com/kubernetes/kubernetes/commit/b926aba2689f5f89de9a13e3a647aab7ee0aa108
5. e2e: node: devices: improve the node reboot test - https://github.com/kubernetes/kubernetes/commit/5cf50105a2b58ae5660d68df729b8a609fa01536
6. e2e: node: add test to check device-requiring pods are cleaned up - https://github.com/kubernetes/kubernetes/commit/d78671447f22203e13b83eb03dabe728718fdaaf
7. node: devicemgr: topomgr: add logs - https://github.com/kubernetes/kubernetes/commit/c635a7e7d8362ac7c706680e77f7680895b1d517
8. Merge pull request https://github.com/kubernetes/kubernetes/pull/119324 from xmudrii/go1206 - https://github.com/kubernetes/kubernetes/commit/5c96e5321e6b4c4875cdbc61c121c27e3e1f189d
9. Merge pull request https://github.com/kubernetes/kubernetes/pull/116470 from alexanderConstantinescu/kep-3836-impl - https://github.com/kubernetes/kubernetes/commit/f34365789d4161f1b47f998bc82250620eed183b
10. Merge pull request https://github.com/kubernetes/kubernetes/pull/118635 from ffromani/devmgr-check-pod-running - https://github.com/kubernetes/kubernetes/commit/900237fada63a88b0b1dbb5f8a20ae73b959df12
```

Note: [PyDriller](https://github.com/ishepard/pydriller) is built around [GitPython](https://github.com/gitpython-developers/GitPython)
and the latter is used in a couple of places to support progress bars for git clone operations and execute raw git commands.

Requires Python 3.6 or greater.

### Installation & run:
```shell
❯ pip3 install -r requirements.txt
❯ python3 differ.py --help
usage: differ.py [-h] --config_file CONFIG_FILE [--releases_file RELEASES_FILE] [-d]

optional arguments:
  -h, --help            show this help message and exit
  --config_file CONFIG_FILE
                        buckets configuration file path
  --releases_file RELEASES_FILE
                        releases file path that contains additional commit information to merge with buckets config file
  -d, --debug           debug mode
❯ python3 differ.py --config_file ./config.yaml (optional: --releases_file ./releases.yaml)
```

### Project structure:
```text
❯ tree -I 'venv|cache|*.txt|*.md' .
.
├── config.yaml   # default (parent) buckets configuration file 
├── differ.py     # main entry point
├── parsers.py    # collection of repository parsers classes
├── releases.yaml # optional: file with additional configuration to use with parent config file
└── utils.py      # collection of utility functions 
```

### Single bucket configuration:
```yaml
buckets:
  - name: MyBucketName            # bucket name
      parser: GitRepoCommitPretty # class name from parsers package 
      repository_params:
        # local and remote repositories are supported 
        path_to_repo: "git@github.com:<org/user>/<repo>.git"
        clone_repo_to: "./cache"
        # all other parameters that pydriller.repository class supports:
        # see https://pydriller.readthedocs.io/en/latest/repository.html#selecting-projects-to-analyze
      parser_params:
        # all parameters that parser class supports:
        # see parser_params attributes of parser classes
```

### RELEASES_FILE configuration:

If no `--releases_file` arg is provided as a script argument all the buckets specified in `--config_file` configuration file are processed. 
In case `--releases_file` is set, for each bucket in `--releases_file` configuration file the bucket configuration is merged into 
`repository_params` of the parent bucket under `--config_file` and only these buckets are processed.

Current merge schema:
```text
buckets:
  - name: MyBucketName               # -> name of the bucket in config_file                 
    commits:
      from_commit: commit_SHA # -> repository_params.from_commit 
      to_commit: commit_SHA    # -> repository_params.to_commit
```

### Setting up new parsers:

1. Define new parser class in `parsers` package as a child class of `parsers.GitRepositoryParser`
2. Write logic around new attributes to support via bucket `parser_params`
3. Have the bucket configured accordingly
4. Update `Readme.md` with new functionality