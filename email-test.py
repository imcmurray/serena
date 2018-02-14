import requests, subprocess, os, sys, time


def email_encrypted_file(filename, emailInfo):

        if os.path.isfile(filename):
                encrypt_cmd = subprocess.Popen(
                        "openssl smime -encrypt -aes256 -in "+filename+" -binary -outform DEM -out "+emailInfo['encrypted_filename']+" /home/pi/Serena/publickey.pem", 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        shell=True
                )
                try:
                        encrypt_cmd.communicate()
                except:
                        print 'Unable to encrypt file!'
                        return(1)
        else:
                print 'Original file not found! [%s]'% filename
                return(1)

        if os.path.isfile(emailInfo['encrypted_filename']):
                emailString = "to:"+emailInfo['to']+"\nsubject:"+emailInfo['subject']+"\n"+emailInfo['message']+"\n"
                email_cmd = subprocess.Popen(
                        "echo -e '"+emailString+"'| (cat - && uuencode "+emailInfo['encrypted_filename']+") | ssmtp "+emailInfo['to'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True
                )

                try:
                        email_cmd.communicate()
                        return(0)
                except:
                        print 'Unable to email encrypted file!'
                        return(1)
        else:
                print 'Encrypted file not found!'
                return(1)


emailDict = {
        'to': 'serena.utb@gmail.com',
        'subject': 'Motion Detected TRB 5th SR - Test #5',
        'message': 'This is the body of the email - Yes Bob!!!',
        'encrypted_filename': '/tmp/TRB_5th_SR_20170717-115337.bin'
}

email_encrypted_file('/home/pi/Serena/capturedMotion/65ae194f-0336-4b8f-972d-6803ea88f2f3/20170717-115337.jpg', emailDict)
