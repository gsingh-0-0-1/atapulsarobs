const express = require('express')
const bodyParser = require('body-parser')
var fs = require('fs');
const {URLSearchParams} = require('url')

const app = express()
const port = 8080

const http = require('http')
const server = http.createServer(app)

app.use(express.static('./public'));

const OBS_RUNS_DIR = "/mnt/datac-netStorage-40G/projects/p009"

app.get("/", (req, res) => {
    res.sendFile("public/templates/main.html", {root: __dirname})
})

app.get("/obsruns", (req, res) => {
    fs.readdir(OBS_RUNS_DIR, (err, files) => {
        res.send(files.join(","))
    })
})

server.listen(port, '0.0.0.0')


