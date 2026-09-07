@echo off
set JAVA_HOME=C:\Users\HP\Downloads\NyaySetu-Pro-Emergent\jre21\jdk-21.0.3+9-jre
set PATH=%JAVA_HOME%\bin;%PATH%
cd /d C:\Users\HP\Downloads\NyaySetu-Pro-Emergent\backend
npx firebase emulators:start --only firestore
