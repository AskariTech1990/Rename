const {app , BrowserWindow} = require('electron')

function createWindow(){
    const win = new BrowserWindow({
        width:1300,
        height:1000,
        title:'Trading App',
        // frame:false,
        webPreferences:{
            nodeIntegration:true
        }
    })
    win.loadFile('index.html')
    // win.webContents.openDevTools()
}
app.whenReady().then(createWindow)