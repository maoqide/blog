---
title: "Build Blog With Hugo"
date: "2018-12-04T18:37:11+08:00"
author: "Maoqide"
tags: ["notes", "blog"]
draft: false
---

how to build your own blog using hugo.    
<!--more--> 

## documentations
[https://gohugo.io/getting-started/usage/](https://gohugo.io/getting-started/usage/)
[https://learn.netlify.com/en/](https://learn.netlify.com/en/)

## setup
1. install hugo following [offical install guide](https://gohugo.io/getting-started/installing/).    
	download packages from [Hugo Release](https://github.com/gohugoio/hugo/releases) and put executale file `hugo` in `PATH`.

2. execute `hugo new site sitename`, To create a new site. directory structure will like this:     
```
.
├── archetypes
├── assets
├── config.toml
├── content
├── data
├── layouts
├── static
└── themes
```

3. download theme from [github](https://github.com/matcornic/hugo-theme-learn/archive/master.zip). unzip the archive and copy files to you site dir, overwriting directory and files of the same name. you can change your website config by changing `config.toml`.

4. wirte you first blog. `hugo new content/first.md`, will gen a markdown file in `content`. you can use `hugo server -w` to start a server locally, and visit [localhost:1313](localhost:1313) for preview.

5. execute `hugo`, this will gen `md` files in dir `content` to `html` files in dir `public`.

6. put your `public` directory in a [nginx](https://www.nginx.com/resources/wiki/).

## menu
directorys in directory `content` will display as menu in the left. and file named `_index.md` is the default page of the directory.


## example
you can visit my github repo [hugo-blog](https://github.com/maoqide/hugo-docs), the article itself is generated by this repo.

## change theme
you can change your styles by changing different themes. themes could be found at [http://themes.gohugo.io](http://themes.gohugo.io).

## overall
overall, you can easily create your own doc/blog by follow command:
```shell
# create a new site
hugo new site mysite
cd mysite/
# create your first page
hugo new first.md
# build page
hugo
```

then you can find your site in directory `public`.