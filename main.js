const express = require('express')
const bodyParser = require('body-parser')
var fs = require('fs');
const {URLSearchParams} = require('url')
const serveIndex = require('serve-index');

const app = express()
const port = 8080

const http = require('http')
const server = http.createServer(app)

app.use("/public", express.static(__dirname + '/public'));
app.use("/pulsar_data", serveIndex(__dirname + '/pulsar_data'));
app.use("/pulsar_data", express.static(__dirname + '/pulsar_data'));

const OBS_RUNS_DIR = "/mnt/datac-netStorage-40G/projects/p009"

app.get("/", (req, res) => {
    res.sendFile("public/templates/main.html", {root: __dirname})
})

app.get("/obsruns", (req, res) => {
    fs.readdir(OBS_RUNS_DIR, (err, files) => {
        res.send(files.join(","))
    })
})

app.get("/targetlist/:run", (req, res) => {
    fs.readdir(OBS_RUNS_DIR + "/" + req.params.run, (err, files) => {
        res.send(files.join("|"))
    })
})

server.listen(port, '0.0.0.0')


