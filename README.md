# Vassal - automated terminal

<img title="vassal_logo" src="https://s3.amazonaws.com/aws-website-shawnshancom-tm5f7/styles/logo.png" data-canonical-src="https://s3.amazonaws.com/aws-website-shawnshancom-tm5f7/styles/logo.png" width="250" height="250"/>

[![license](https://img.shields.io/github/license/mashape/apistatus.svg?maxAge=2592000)](https://github.com/Shawn-Shan/vassal/blob/master/LICENSE)

Vassal is a python package provide terminal automation. Save developers unnecessary labor to type in tons of duplicated and similar commands. 

## Getting Started

1. Run a list of commands on a ssh server

```
from vassal.terminal import Terminal
shell = Terminal(["ssh username@host", "cd scripts", "python foo1.py", "python foo2.py"])
shell.run()
```

2. upload/download files through scp

```
shell = Terminal(["scp username@host:/home/foo.txt foo_local.txt"])
shell.run()
```

### Installing

```
pip install vassal
```

## Built With

* [paramiko](http://www.paramiko.org/) - SSHv2 protocol

## Contributing

Please read [CONTRIBUTING.md](https://github.com/Shawn-Shan/vassal/blob/master/CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Authors

* **Shawn Shan** - *Initial work* - [https://www.shawnshan.com/](https://www.shawnshan.com/)


## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/Shawn-Shan/vassal/blob/master/LICENSE) file for details
