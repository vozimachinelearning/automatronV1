@echo off
cd /d %~dp0

git add .
git commit -m "Automated commit"
git push origin main

echo Changes have been pushed to the main branch.
pause