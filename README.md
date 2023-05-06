# simple_cloudflare_ddns
Cloudflare DDNS

# TODO
- [ ] Update Usage
- [ ] Add argparse support
- [ ] Add logging file support
- [ ] Add typing support
- [ ] Add unit test

# Windows Schedule
1. add schedule task
```powershell
schtasks /create /tn "DDNS" /tr "C:\Users\chenfei\ddns\main.exe" /sc minute /mo 1 /ru System
```
2. delete schedule task
```powershell
schtasks /delete /tn "DDNS" /f
```
3. query schedule task
```powershell
schtasks /query /tn "DDNS"
```
4. run schedule task
```powershell
schtasks /run /tn "DDNS"
```
