const express = require('express')
const bodyParser = require('body-parser')
var fs = require('fs');
const {URLSearchParams} = require('url')
const serveIndex = require('serve-index');

const app = express()
const port = 8080

const http = require('http')
const server = http.createServer(app)
const child_process = require('child_process');
const glob = require("glob")

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

app.get("/images/:obs/:targetdir/:LO", (req, res) => {
    fs.readdir("pulsar_data/" + req.params.obs + "/" + req.params.targetdir + "/" + req.params.LO, (err, files) => {
        res.send(files.join("|"))
    })
})

app.get("/exec/:cmd/:args", (req, res) => {
    var cmd = req.params.cmd
    var args = req.params.args
    var arglist = args.split(" ")

    if (cmd === "procobs") {
        var targetobs = arglist[0]
        var cmd = "/home/gsingh/pulsar_analysis/ar_image_gen.sh"
        var proc = child_process.spawn("bash", [cmd, targetobs], {detached : true, stdio: ['ignore', 'ignore', 'ignore']})
        /*proc.stdout.on('data', function (data) {
            console.log(data.toString());
        });
        proc.stderr.on('data', function (data) {
            console.log(data.toString());
        });*/
        res.send("executing...");
    }
})

app.get("/list/*", (req, res) => {
    console.log(req.params['0'])
    glob(req.params['0'], function (err, files) {
        res.send(files.join("|"))
    })
})

server.listen(port, '0.0.0.0')


