# coding: utf-8
#Sylvain Kritter 21 septembre 2016
""" generate predict and visu with lung in bmp file already there """
#general parameters and file, directory names"

import os
import cv2
import datetime
import time
import dicom
import scipy
import sys
import shutil
import numpy as np
#import Tkinter as Tk

import PIL
from PIL import Image as ImagePIL
from PIL import  ImageFont, ImageDraw 
import cPickle as pickle
import ild_helpers as H
import cnn_model as CNN4
from keras.models import model_from_json
from Tkinter import *

#global environment

picklefileglobal='MHKpredictglobal.pkl'
instdirMHK='MHKpredict'
workdiruser='Documents/boulot/startup/radiology/PREDICT'

tempofile=os.path.join(os.environ['TMP'],picklefileglobal)
workingdir= os.path.join(os.environ['USERPROFILE'],workdiruser)
instdir=os.path.join(os.environ['LOCALAPPDATA'],instdirMHK)


#########################################################
#picklefile='pickle_sk32'
#picklefile='pickle_sk8_lung'
picklefile='pickle_sk12_lung'
dimpavx =15
dimpavy = 15

cMean=True # if data are centered on mean
# with or without bg (true if with back_ground)
wbg=True

globalHist=True #use histogram equalization on full image

contrastScan=False #to enhance contrast on patch put True
#normalization internal procedure or openCV
normiInternal=False

#path for visua back-ground
vbg='A'
#threshold for patch acceptance overlapp
thrpatch = 0.9
#threshold for probability prediction
thrproba = 0.5
#probability for lung acceptance
thrlung=0.7

#subsample by default
subsdef=10
imageDepth=255 #number of bits used on dicom images (2 **n)
#can be 255 or 512

# average pxixel spacing
avgPixelSpacing=0.734
#workingdirectory='C:\Users\sylvain\Documents\boulot\startup\radiology\PREDICT'
#installdirectory='C:\Users\sylvain\Documents\boulot\startup\radiology\UIP\python'
#global directory for predict file
namedirtop = 'predict_essai'

#directory for storing image out after prediction
predictout='predicted_results'

#directory with lung mask dicom
lungmask='lung_mask'

#directory to put  lung mask bmp
lungmaskbmp='bmp'

#directory name with scan with roi
sroi='sroi'

#subdirectory name to put images
jpegpath = 'patch_jpeg'

#directory with bmp from dicom
scanbmp='scan_bmp'

Xprepkl='X_predict.pkl'
Xrefpkl='X_file_reference.pkl'

lungXprepkl='lung_X_predict.pkl'
lungXrefpkl='lung_X_file_reference.pkl'

#file to store different parameters
subsamplef='subsample.pkl'

#subdirectory name to colect pkl files for prediction
modelname= 'ILD_CNN_model.h5'
#image  patch format
typei='bmp' 

#dicom file size in pixels
#dimtabx = 512
#dimtaby = 512
excluvisu=['nolung']
#excluvisu=['']

#########################################################################
if imageDepth !=255 and imageDepth != 512:
        print 'ERROR:',imageDepth,' is not 255 or 512'
        sys.exit()
if contrastScan:
    if normiInternal:
        print 'Internal contrast enabled'
    else:
        print 'openCv contrast enabled'
else:
        print 'no contrast'
cwd=os.getcwd()
glovalf=tempofile
path_patient = os.path.join(workingdir,namedirtop)
varglobal=(thrpatch,thrproba,path_patient,subsdef)

def setva():
        global varglobal,thrproba,thrpatch,subsdef,path_patient
        if not os.path.exists(glovalf) :
            pickle.dump(varglobal, open( glovalf, "wb" ))
        else:
            dd = open(glovalf,'rb')
            my_depickler = pickle.Unpickler(dd)
            varglobal = my_depickler.load()
            dd.close() 
#            print varglobal
            path_patient=varglobal[2]
#            print path_patient
            thrproba=varglobal[1]
            thrpatch=varglobal[0]
            subsdef=varglobal[3]



def newva():
 pickle.dump(varglobal, open( glovalf, "wb" ))


(cwdtop,tail)=os.path.split(cwd)

#if not os.path.exists(path_patient):
#    print 'patient directory does not exists'
#    sys.exit()

setva()   
picklein_file = os.path.join(instdir,picklefile)
print 'path pickle :',picklein_file
if not os.path.exists(picklein_file):
    print 'model and weight directory does not exists'
    sys.exit()
lpck= os.listdir(picklein_file)
pson=False

for l in lpck:
    if l.find('.h5',0)>0:
        pson=True
if not( pson):
    print 'model and weight files does not exists'
    sys.exit()     



pxy=float(dimpavx*dimpavy)

#end general part
#font file imported in top directory
font20 = ImageFont.truetype( 'arial.ttf', 20)
font10 = ImageFont.truetype( 'arial.ttf', 10)
#########################################################
errorfile = open(path_patient+'/predictlog.txt', 'w') 

#color of labels
black=(0,0,0)
red=(255,0,0)
green=(0,255,0)
blue=(0,0,255)
yellow=(255,255,0)
cyan=(0,255,255)
purple=(255,0,255)
white=(255,255,255)
darkgreen=(11,123,96)
pink =(255,128,150)
lightgreen=(125,237,125)
orange=(255,153,102)
lowgreen=(0,51,51)

classif={
    'nolung':0,
    'lung':1,}
    
classifc ={
'nolung':red,
'lung':white
 }
#only label we consider, number will start at 0 anyway

def rsliceNum(s,c,e):
    ''' look for  afile according to slice number'''
    #s: file name, c: delimiter for snumber, e: end of file extension
    endnumslice=s.find(e)
    posend=endnumslice
    while s.find(c,posend)==-1:
        posend-=1
    debnumslice=posend+1
    return int((s[debnumslice:endnumslice])) 

def remove_folder(path):
    """to remove folder"""
    # check if folder exists
    if os.path.exists(path):
         # remove if exists
         shutil.rmtree(path,ignore_errors=True)

   
def genebmp(dirName,fn,subs):
    """generate patches from dicom files"""
    global dimtabx, dimtaby
#    print ('load dicom files in :',dirName, 'scan name:',fn)
    #directory for patches
    bmp_dir = os.path.join(dirName, scanbmp)
    FilesDCM =(os.path.join(dirName,fn))  
    RefDs = dicom.read_file(FilesDCM)
    dsr= RefDs.pixel_array
    dsr= dsr-dsr.min()
    c=255.0/dsr.max()
    dsr=dsr*c
    if imageDepth ==255:
        dsr=dsr.astype('uint8')
    elif imageDepth ==512:
        dsr=dsr.astype('uint16')
    else:
        print 'ERROR:',imageDepth,' is not 255 or 512'
#    constPixelSpacing=(float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1]), float(ds.SliceThickness))
    fxs=float(RefDs.PixelSpacing[0])/avgPixelSpacing
#    fys=float(dsr.PixelSpacing[1])/avgPixelSpacing
    scanNumber=int(RefDs.InstanceNumber)
    endnumslice=fn.find('.dcm')
    imgcore=fn[0:endnumslice]+'_'+str(scanNumber)+'.'+typei
    bmpfile=os.path.join(bmp_dir,imgcore)   
#    scipy.misc.imsave(bmpfile, ds.pixel_array)
#    imgor=cv2.imread(bmpfile)
    dsrresize1= scipy.misc.imresize(dsr,fxs,interp='bicubic',mode=None)
#    dsrresize1=cv2.resize(dsr,None,fx=fxs,fy=fys,interpolation=cv2.INTER_LINEAR)
    if globalHist:
        if normiInternal:
            dsrresize = normi(dsrresize1) 
        else:
            dsrresize = cv2.equalizeHist(dsrresize1) 
    else:
            dsrresize=dsrresize1
    cv2.imwrite(bmpfile,dsrresize)

    dimtabx=dsrresize.shape[0]
    dimtaby=dsrresize.shape[1]
#    print dimtabx
    
   
    


def normi(tabi):
     """ normalise patches 0 255"""

     tabi1=tabi-tabi.min()

     tabi2=tabi1*(imageDepth/float(tabi1.max()-tabi1.min()))
     if imageDepth<256:
         tabi2=tabi2.astype('uint8')
     else:
         tabi2=tabi2.astype('uint16')

     return tabi2

    
def pavgene (namedirtopcf):
        """ generate patches from scan"""
        global patch_list
#        print('generate patches on: ',namedirtopcf)
        (dptop,dptail)=os.path.split(namedirtopcf)
#        print namemask
        bmpdir = os.path.join(namedirtopcf,scanbmp)
        jpegpathf=os.path.join(namedirtopcf,jpegpath)
        
        listbmp= os.listdir(bmpdir)
#        print(listbmp)

                
        for img in listbmp:
#             print img
             slicenumber=rsliceNum(img,'_','.bmp')
#             endnumslice=img.find('.bmp')
#             posend=endnumslice
#             while img.find('_',posend)==-1:
#                     posend-=1
#             debnumslice=posend+1
#             slicenumber=int(img[debnumslice:endnumslice])         

             bmpfile = os.path.join(bmpdir,img)
             tabf = cv2.imread(bmpfile,1)
#             im = ImagePIL.open(bmpfile)

#             cv2.imshow('image',tablung) 
#             cv2.waitKey(0)

             xmin=0
             xmax=dimtabx-dimpavx
             ymin=0
             ymax=dimtaby-dimpavy
                
             i=xmin
#             print xmin,xmax,ymin,ymax
             while i <= xmax:
                 j=ymin
        #        j=maxj
                 while j<=ymax:

                        crorig = tabf[j:j+dimpavy,i:i+dimpavx]
                        imgra =np.array(crorig)
                        imgray = cv2.cvtColor(imgra,cv2.COLOR_BGR2GRAY)
                        imagemax= cv2.countNonZero(imgray)
                        min_val, max_val, min_loc,max_loc = cv2.minMaxLoc(imgray)
             
                        if imagemax > 0 and max_val-min_val>10:
#                            if i==120 and j==60:
#                                print min_val, max_val, min_loc,max_loc
                                
#                            namepatch=patchpathf+'/p_'+str(slicenumber)+'_'+str(i)+'_'+str(j)+'.'+typei
                            if contrastScan:
                                    if normiInternal:
#                                        print 'internal normalization'
                                        tabi2=normi(imgray)
                                    else:
#                                        print 'opencv nomalization'
                                        tabi2 = cv2.equalizeHist(imgray)
                                    patch_list.append((dptail,slicenumber,i,j,tabi2))
#                                    if i==480 and j==315:
#                                        print (dptail,slicenumber,i,j,tabi2)
#                                        print tabi2.shape, dimtabx, dimtaby, dimpavx, dimpavy
#                                    n+=1
                            else:
#                                print 'no contrast'
                                patch_list.append((dptail,slicenumber,i,j,imgray))
                            
#                            tablung[j:j+dimpavy,i:i+dimpavx]=0
                            x=0
                            while x < dimpavx:
                                y=0
                                while y < dimpavy:
                                    if y+j<dimtaby and x+i<dimtabx:
                                        tabf[y+j][x+i]=[255,0,0]
                                    if x == 0 or x == dimpavx-1 :
                                        y+=1
                                    else:
                                        y+=dimpavy-1
                                x+=1                                             
                        j+=dimpavy
#                     j+=dimpavy
                 i+=dimpavx
#                 i+=1
#        print namedirtopcf,n
             scipy.misc.imsave(jpegpathf+'/'+'s_'+str(slicenumber)+'.bmp', tabf)
# 
def ILDCNNpredict(patient_dir_s):     
        
#        print ('predict patches on: ',patient_dir_s) 
        (top,tail)=os.path.split(patient_dir_s)
        print ('predict patches on: ',top) 
        for fil in patch_list:
            if fil[0]==tail:
#                print fil[0]
               
                dataset_list.append(fil[4])
                nameset_list.append(fil[0:3])
 
       
        X = np.array(dataset_list)
#        print X.shape
#        print X[1]
        X0= X.shape[0]
        if imageDepth<256:
            dcf=float(255)
        else:
            dcf=float(512)
        X_predict1 = np.asarray(np.expand_dims(X,1))/dcf
        if cMean:
            m=np.mean(X_predict1)
#            print 'mean of Xtrain :',m
            X_predict=X_predict1-m
        else:
            X_predict=X_predict1        
##        print picklein_file
#        jsonf= os.path.join(picklein_file,'ILD_CNN_model.json')
#        print jsonf
#        weigf= os.path.join(picklein_file,'ILD_CNN_model_weights')
        

#        print weigf
#model and weights fr CNN
        args  = H.parse_args()                          
        train_params = {
     'do' : float(args.do) if args.do else 0.4,        
     'a'  : float(args.a) if args.a else 0.3,          # Conv Layers LeakyReLU alpha param [if alpha set to 0 LeakyReLU is equivalent with ReLU]
     'k'  : int(args.k) if args.k else 4,              # Feature maps k multiplier
     's'  : float(args.s) if args.s else 1,            # Input Image rescale factor
     'pf' : float(args.pf) if args.pf else 1,          # Percentage of the pooling layer: [0,1]
     'pt' : args.pt if args.pt else 'Avg',             # Pooling type: Avg, Max
     'fp' : args.fp if args.fp else 'proportional',    # Feature maps policy: proportional, static
     'cl' : int(args.cl) if args.cl else 5,            # Number of Convolutional Layers
     'opt': args.opt if args.opt else 'Adam',          # Optimizer: SGD, Adagrad, Adam
     'obj': args.obj if args.obj else 'ce',            # Minimization Objective: mse, ce
     'patience' : args.pat if args.pat else 5,         # Patience parameter for early stoping
     'tolerance': args.tol if args.tol else 1.005,     # Tolerance parameter for early stoping [default: 1.005, checks if > 0.5%]
     'res_alias': args.csv if args.csv else 'res'      # csv results filename alias
         }
#        model = H.load_model()
        
        modelfile= os.path.join(picklein_file,modelname)
        model= H.load_model(modelfile)

        model.compile(optimizer='Adam', loss=CNN4.get_Obj(train_params['obj']))        
    
        if X0>0:
            proba = model.predict_proba(X_predict, batch_size=100)
        else:
            proba=()
#        print proba[0]
        picklefileout_f_dir = os.path.join( patient_dir_s,picklefile)     
        xfp=os.path.join(picklefileout_f_dir,Xprepkl)
        pickle.dump(proba, open( xfp, "wb" ))
        xfpr=os.path.join(picklefileout_f_dir,Xrefpkl)
        pickle.dump(patch_list, open( xfpr, "wb" ))
#        print proba[0]


def fidclass(numero,classn):
    """return class from number"""
    found=False
    for cle, valeur in classn.items():
        
        if valeur == numero:
            found=True
            return cle
      
    if not found:
        return 'unknown'

 
def tagview(fig,label,pro,x,y):
    """write text in image according to label and color"""

    col=classifc[label]
#    print col, label
    if wbg :
        labnow=classif[label]-1
    else:
        labnow=classif[label]
#    print (labnow, text)
    if label == 'back_ground':
        x=0
        y=0        
        deltax=0
        deltay=60
    else:        
        deltay=11*((labnow)%5)
        deltax=175*((labnow)//5)

    cv2.putText(fig,label+' '+pro,(x+deltax, y+deltay+10),cv2.FONT_HERSHEY_PLAIN,0.8,col,1)

    
def tagviews(b,fig,t0,x0,y0,t1,x1,y1,t2,x2,y2,t3,x3,y3,t4,x4,y4):
    """write simple text in image """
    imgn=ImagePIL.open(fig)
    draw = ImageDraw.Draw(imgn)
    if b:
        draw.rectangle ([x1, y1,x1+100, y1+15],outline='black',fill='black')
        draw.rectangle ([140, 0,dimtabx,75],outline='black',fill='black')
    draw.text((x0, y0),t0,white,font=font10)
    draw.text((x1, y1),t1,white,font=font10)
    draw.text((x2, y2),t2,white,font=font10)
    if not b:
        draw.text((x3, y3),t3,white,font=font10)
    draw.text((x4, y4),t4,white,font=font10)
    imgn.save(fig)

def maxproba(proba):
    """looks for max probability in result"""
    lenp = len(proba)
    m=0
    for i in range(0,lenp):
        if proba[i]>m:
            m=proba[i]
            im=i
    return im,m


def loadpkl(do):
    """crate image directory and load pkl files"""
#    global classdirec
    
    picklefileout_f_dir = os.path.join( do,picklefile)
    xfp=os.path.join(picklefileout_f_dir,Xprepkl)
    dd = open(xfp,'rb')
    my_depickler = pickle.Unpickler(dd)
    probaf = my_depickler.load()
    dd.close()  
    
    xfpr=os.path.join(picklefileout_f_dir,Xrefpkl)
    dd = open(xfpr,'rb')
    my_depickler = pickle.Unpickler(dd)
    patch_listr = my_depickler.load()
    dd.close() 
    
    preprob=[]
    prefile=[]
    
    (top,tail)=os.path.split(do)

    n=0
    for fil in patch_listr:        
        if fil[0]==tail:
#            print n, proba[n]
            preprob.append(probaf[n])
            prefile.append(fil[1:4])
        n=n+1
    return (preprob,prefile)


def drawContour(imi,ll):
    
    vis = np.zeros((dimtabx,dimtaby,3), np.uint8)
    for l in ll:
#        print l
        col=classifc[l]

        masky=cv2.inRange(imi,col,col)
        outy=cv2.bitwise_and(imi,imi,mask=masky)
        imgray = cv2.cvtColor(outy,cv2.COLOR_BGR2GRAY)
        ret,thresh = cv2.threshold(imgray,0,255,0)
        im2,contours0, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,\
        cv2.CHAIN_APPROX_SIMPLE)        
        contours = [cv2.approxPolyDP(cnt, 0, True) for cnt in contours0]
#        cv2.drawContours(vis,contours,-1,col,1,cv2.LINE_AA)
        cv2.drawContours(vis,contours,-1,col,1)

    return vis

def tagviewn(fig,label,pro,nbr,x,y):
    """write text in image according to label and color"""

    col=classifc[label]
#    print col, label
    if wbg :
        labnow=classif[label]-1
    else:
        labnow=classif[label]
#    print (labnow, text)
    if label == 'back_ground':
        x=0
        y=0        
        deltax=0
        deltay=60
    else:        
        deltay=11*((labnow)%5)
        deltax=175*((labnow)//5)

    cv2.putText(fig,str(nbr)+' '+label+' '+pro,(x+deltax, y+deltay+10),cv2.FONT_HERSHEY_PLAIN,0.8,col,1)

def  visua(dirpatientdb,cla,wra):

    (dptop,dptail)=os.path.split(dirpatientdb)
    if cla==1:
        topdir=dptail
    else:
        (dptop1,dptail1)=os.path.split(dptop)
        topdir=dptail1
#        print 'topdir visua',topdir
    for i in range (0,len(classif)):
#        print 'visua dptail', topdir
        listelabelfinal[topdir,fidclass(i,classif)]=0
    #directory name with predict out dabasase, will be created in current directory
    predictout_dir = os.path.join(dirpatientdb, predictout)
    predictout_dir_bv = os.path.join(predictout_dir,vbg)
    predictout_dir_th = os.path.join(predictout_dir,str(thrproba))
    (preprob,listnamepatch)=loadpkl(dirpatientdb)
#    print preprob[0], listnamepatch
    dirpatientfdb=os.path.join(dirpatientdb,scanbmp)
    dirpatientfsdb=os.path.join(dirpatientdb,sroi)
    listbmpscan=os.listdir(dirpatientfdb)
#    print dirpatientfdb
    listlabelf={}
    for img in listbmpscan:
        imgt = np.zeros((dimtabx,dimtaby,3), np.uint8)
        listlabelaverage={}
        listlabel={}
        listlabelrec={}
        if os.path.exists(dirpatientfsdb):
            imgc=os.path.join(dirpatientfsdb,img)
        else:
            imgc=os.path.join(dirpatientfdb,img)
 
        endnumslice=img.find('.'+typei)
        imgcore=img[0:endnumslice]
#        print imgcore
#        posend=endnumslice
#        while img.find('-',posend)==-1:
#            posend-=1
#        debnumslice=posend+1
#        slicenumber=int((img[debnumslice:endnumslice])) 
        slicenumber=rsliceNum(img,'_','.'+typei)
        tablscan=cv2.imread(imgc,1)
#        tablscan = cv2.cvtColor(tablscan, cv2.COLOR_BGR2RGB)
#        imscan = ImagePIL.open(imgc)
#        imscanc= imscan.convert('RGB')
#        tablscan = np.array(imscanc)
#        if imscan.size[0]>512:
#            ncr=imscanc.resize((dimtabx,dimtaby),PIL.Image.ANTIALIAS)
#            tablscan = np.array(ncr) 
        ill = 0
        
      
        foundp=False
        for ll in listnamepatch:
#            print ll
            slicename=ll[0] 
            xpat=ll[1]
            ypat=ll[2]
            proba=preprob[ill]          
            prec, mprobai = maxproba(proba)
            mproba=round(mprobai,2)
            classlabel=fidclass(prec,classif) 
            classcolor=classifc[classlabel]
#            print slicenumber, slicename,dptail
            if slicenumber == slicename and\
            (classlabel not in excluvisu):
#                    print slicenumber, slicename,dptail
                    foundp=True
                    if classlabel in listlabel:
                        numl=listlabel[classlabel]
                        listlabel[classlabel]=numl+1
                    else:
                        listlabel[classlabel]=1
                    if classlabel in listlabelf:
                        nlt=listlabelf[classlabel]
                        listlabelf[classlabel]=nlt+1
                    else:
                        listlabelf[classlabel]=1
            
            if mproba >thrproba and slicenumber == slicename and\
              (classlabel not in excluvisu):
                      
                      
#                    print mproba,xpat,ypat,classlabel
                    if classlabel in listlabelrec:
                        numl=listlabelrec[classlabel]
                        listlabelrec[classlabel]=numl+1
                        cur=listlabelaverage[classlabel]
                        averageproba= round((cur*numl+mproba)/(numl+1),2)
                        listlabelaverage[classlabel]=averageproba
                    else:
                        listlabelrec[classlabel]=1
                        listlabelaverage[classlabel]=mproba

                    imgi=addpatch(classcolor,classlabel,xpat,ypat,dimpavx,dimpavy)
#                    cv2.imshow('scan',imgi) 
##        cv2.imshow('lung',listlungdict) 
#                    cv2.waitKey(0)    
#                    cv2.destroyAllWindows()
                    imgt=cv2.add(imgt,imgi)
            
                        
                        

            ill+=1
#        cv2.imshow('scan',imgt) 
##        cv2.imshow('lung',listlungdict) 
#        cv2.waitKey(0)    
#        cv2.destroyAllWindows()
        if wra:        
            imgcorefull=imgcore+'.bmp'
            imgnameth=os.path.join(predictout_dir_th,imgcorefull)
            imgnamebv=os.path.join(predictout_dir_bv,imgcorefull)
    #        print 'imgname',imgname    
            cv2.imwrite(imgnamebv,tablscan)
            tablscan = cv2.cvtColor(tablscan, cv2.COLOR_BGR2RGB)

            vis=drawContour(imgt,listlabel)
#            vis = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)

#put to zero the contour in image in order to get full visibility of contours
            img2gray = cv2.cvtColor(vis,cv2.COLOR_BGR2GRAY)
            ret, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
            mask_inv = cv2.bitwise_not(mask)
#            print dimtabx
#            print mask_inv.shape, tablscan.shape
            img1_bg = cv2.bitwise_and(tablscan,tablscan,mask = mask_inv)  
#superimpose scan and contours      
#            print img1_bg.shape, vis.shape
            imn=cv2.add(img1_bg,vis)


            if foundp:
#            tagviews(imgname,'average probability',0,0)           
                for ll in listlabelrec:
                    tagviewn(imn,ll,str(listlabelaverage[ll]),listlabelrec[ll],175,00)
            else:   
#            tagviews(imgname,'no recognised label',0,0)
                errorfile.write('no recognised label in: '+str(topdir)+' '+str (img)+'\n' )

            imn = cv2.cvtColor(imn, cv2.COLOR_BGR2RGB)
#            cv2.imwrite(imgnamebv,tablscan)
            cv2.imwrite(imgnameth,imn)            
            
       
            if foundp:
                t0='average probability'
            else:
                t0='no recognised label'
            t1='n: '+topdir+' scan: '+str(slicenumber)        
            t2='CONFIDENTIAL - prototype - not for medical use'
            t3='For threshold: '+str(thrproba)+' :'
            t4=time.asctime()
            tagviews(True,imgnamebv,t0,0,0,t1,0,20,t2,20,dimtaby-27,t3,0,38,t4,0,dimtaby-10)
            tagviews(False,imgnameth,t0,0,0,t1,0,20,t2,20,dimtaby-27,t3,0,38,t4,0,dimtaby-10)

        
            errorfile.write('\n'+'number of labels in :'+str(topdir)+' '+str(dptail)+str (img)+'\n' )
#    print listlabelf
    for classlabel in listlabelf:  
          listelabelfinal[topdir,classlabel]=listlabelf[classlabel]
          print 'patient: ',topdir,', label:',classlabel,': ',listlabelf[classlabel]
          string=str(classlabel)+': '+str(listlabelf[classlabel])+'\n' 
#          print string
          errorfile.write(string )

#    
def renomscan(fa):
        num=0
        contenudir = os.listdir(fa)
#        print(contenudir)
        for ff in contenudir:
#            print ff
            if ff.find('.dcm')>0 and ff.find('-')<0:     
                num+=1    
                corfpos=ff.find('.dcm')
                cor=ff[0:corfpos]
                ncff=os.path.join(fa,ff)
#                print ncff
                if num<10:
                    nums='000'+str(num)
                elif num<100:
                    nums='00'+str(num)
                elif num<1000:
                    nums='0'+str(num)
                else:
                    nums=str(num)
                newff=cor+'-'+nums+'.dcm'
    #            print(newff)
                shutil.copyfile(ncff,os.path.join(fa,newff) )
                os.remove(ncff)
def dd(i):
    if (i)<10:
        o='0'+str(i)
    else:
        o=str(i)
    return o


def nothings(x):
    global imgtext
    imgtext = np.zeros((dimtabx,dimtaby,3), np.uint8)
    pass

def nothing(x):
    pass

def contrast(im,r):   
     tabi = np.array(im)
     r1=0.5+r/100.0
     tabi1=tabi*r1     
     tabi2=np.clip(tabi1,0,255)
     tabi3=tabi2.astype(np.uint8)
     return tabi3

def lumi(im,r):
    tabi = np.array(im)
    r1=r
    tabi1=tabi+r1
    tabi2=np.clip(tabi1,0,255)
    return tabi2

# mouse callback function
def draw_circle(event,x,y,flags,img):
    global ix,iy,quitl,patchi
    patchi=False

    if event == cv2.EVENT_RBUTTONDBLCLK:
        print x, y
    if event == cv2.EVENT_LBUTTONDBLCLK:
 
#        print('identification')
        ix,iy=x,y
       
        patchi=True
#        print 'identification', ix,iy, patchi
        if x>250 and x<270 and y>dimtaby-30 and y<dimtaby-10:
            print 'quit'
            ix,iy=x,y
            quitl=True

def addpatchn(col,lab, xt,yt,imgn):
#    print col,lab
    cv2.rectangle(imgn,(xt,yt),(xt+dimpavx,yt+dimpavy),col,1)
    return imgn
 
def addpatch(col,lab, xt,yt,px,py):
    imgi = np.zeros((dimtabx,dimtaby,3), np.uint8)
#    colr=[col[2],col[1],col[0]]
#    numl=listlabel[lab]
    tablint=[(xt,yt),(xt,yt+py),(xt+px,yt+py),(xt+px,yt)]
    tabtxt=np.asarray(tablint)
#    print tabtxt
    cv2.polylines(imgi,[tabtxt],True,col)
    cv2.fillPoly(imgi,[tabtxt],col)
    return imgi         
 
 
 
def retrievepatch(x,y,top,sln,pr,li):
    tabtext = np.zeros((dimtabx,dimtaby,3), np.uint8)
    ill=-1
    pfound=False
    for f in li:
        ill+=1 
        slicenumber=f[0]

        if slicenumber == sln:

            xs=f[1]
            ys=f[2]
#            print xs,ys
            if x>xs and x < xs+dimpavx and y>ys and y<ys+dimpavy:
                     print  xs, ys
                     proba=pr[ill]
                     pfound=True

                     n=0
                     cv2.putText(tabtext,'X',(xs-5+dimpavx/2,ys+5+dimpavy/2),cv2.FONT_HERSHEY_PLAIN,1,(0,255,0),1)
                     for j in range (0,len(proba)):
                         
#                     for j in range (0,2):
                         if proba[j]>0.01:
                             n=n+1
                             strw=fidclass(j,classif)+ ' {0:.1f}%'.format(100*proba[j])                             
                             cv2.putText(tabtext,strw,(dimtabx-142,(dimtaby-60)+10*n),cv2.FONT_HERSHEY_PLAIN,0.8,(0,255,0),1)
                             
                             print fidclass(j,classif), ' {0:.2f}%'.format(100*proba[j])
                     print'found'
                     break 
#    cv2.imshow('image',tabtext)                
    if not pfound:
            print'not found'
    return tabtext

def drawpatch(t,lp,preprob,k,top):
    imgn = np.zeros((dimtabx,dimtaby,3), np.uint8)
    ill = 0
#    endnumslice=k.find('.bmp')
#
##    print imgcore
#    posend=endnumslice
#    while k.find('-',posend)==-1:
#            posend-=1
#    debnumslice=posend+1
    slicenumber=rsliceNum(k,'_','.bmp')
#    slicenumber=int((k[debnumslice:endnumslice])) 
    th=t/100.0
    listlabel={}
    listlabelaverage={}
#    print slicenumber,th
    for ll in lp:

#            print ll
            slicename=ll[0]          
            xpat=ll[1]
            ypat=ll[2]        
        #we find max proba from prediction
            proba=preprob[ill]
           
            prec, mprobai = maxproba(proba)
            mproba=round(mprobai,2)
            classlabel=fidclass(prec,classif)
            classcolor=classifc[classlabel]
       
            
            if mproba >th and slicenumber == slicename and\
            ( (classlabel not in excluvisu)):
#                    print classlabel
                    if classlabel in listlabel:
#                        print 'found'
                        numl=listlabel[classlabel]
                        listlabel[classlabel]=numl+1
                        cur=listlabelaverage[classlabel]
#                               print (numl,cur)
                        averageproba= round((cur*numl+mproba)/(numl+1),2)
                        listlabelaverage[classlabel]=averageproba
                    else:
                        listlabel[classlabel]=1
                        listlabelaverage[classlabel]=mproba

                    imgn= addpatchn(classcolor,classlabel,xpat,ypat,imgn)


            ill+=1
#            print listlabel        
    for ll1 in listlabel:
#                print ll1,listlabelaverage[ll1]
                tagviewn(imgn,ll1,str(listlabelaverage[ll1]),listlabel[ll1],175,00)
    ts='Treshold:'+str(t)
#    cv2.putText(imgn,ts,(0,42),cv2.FONT_HERSHEY_PLAIN,1,white,0.8,cv2.LINE_AA)
    cv2.putText(imgn,ts,(0,42),cv2.FONT_HERSHEY_PLAIN,0.8,white,1,cv2.LINE_AA)
    return imgn
    
def opennew(dirk, fl,L):
    pdirk = os.path.join(dirk,L[fl])
    img = cv2.imread(pdirk,1)
    return img,pdirk

def reti(L,c):
    for i in range (0, len(L)):
     if L[i]==c:
         return i
         break
     

def openfichier(k,dirk,top,L):
    nseed=reti(L,k) 
#    print 'openfichier', k, dirk,top,nseed
  
    global ix,iy,quitl,patchi,classdirec
    global imgtext, dimtabx,dimtaby
   
    patchi=False
    ix=0
    iy=0
    ncf1 = os.path.join(path_patient,top)
    dop =os.path.join(ncf1,picklefile)
    if classdirec==2:
        ll=os.listdir(ncf1)
        for l in ll:
            ncf =os.path.join(ncf1,l)
            dop =os.path.join(ncf,picklefile)
    else:
        ncf=ncf1
            
    subsample=varglobal[3]
    pdirk = os.path.join(dirk,k)
    img = cv2.imread(pdirk,1)
    dimtabx= img.shape[0]
    dimtaby= dimtabx
    imgtext = np.zeros((dimtabx,dimtaby,3), np.uint8)
#    print 'openfichier:',k , ncf, pdirk,top
    
    (preprob,listnamepatch)=loadpkl(ncf)      
    
    cv2.namedWindow('image',cv2.WINDOW_NORMAL)

    cv2.createTrackbar( 'Brightness','image',0,100,nothing)
    cv2.createTrackbar( 'Contrast','image',50,100,nothing)
    cv2.createTrackbar( 'Threshold','image',50,100,nothing)
    cv2.createTrackbar( 'Flip','image',nseed,len(L)-1,nothings)
        
    while(1):
        cv2.setMouseCallback('image',draw_circle,img)
        c = cv2.getTrackbarPos('Contrast','image')
        l = cv2.getTrackbarPos('Brightness','image')
        tl = cv2.getTrackbarPos('Threshold','image')
        fl = cv2.getTrackbarPos('Flip','image')

        img,pdirk= opennew(dirk, fl,L)
#        print pdirk
        
        
        (topnew,tailnew)=os.path.split(pdirk)
#        endnumslice=tailnew.find('.bmp',0)
#        posend=endnumslice
#        while tailnew.find('-',posend)==-1:
#            posend-=1
#            debnumslice=posend+1
        slicenumber=rsliceNum(tailnew,'_','.bmp')
#        slicenumber=int((tailnew[debnumslice:endnumslice])) 
        
        imglumi=lumi(img,l)
        imcontrast=contrast(imglumi,c)        
        imcontrast=cv2.cvtColor(imcontrast,cv2.COLOR_BGR2RGB)
#        print imcontrast.shape, imcontrast.dtype
        imgn=drawpatch(tl,listnamepatch,preprob,L[fl],top)
#        imgn=cv2.cvtColor(imgn,cv2.COLOR_BGR2RGB)
        imgngray = cv2.cvtColor(imgn,cv2.COLOR_BGR2GRAY)
#        print imgngray.shape, imgngray.dtype
        mask_inv = cv2.bitwise_not(imgngray)              
        outy=cv2.bitwise_and(imcontrast,imcontrast,mask=mask_inv)
        imgt=cv2.add(imgn,outy)
 
       
        cv2.rectangle(imgt,(250,dimtaby-10),(270,dimtaby-30),red,-1)
        cv2.putText(imgt,'quit',(260,dimtaby-10),cv2.FONT_HERSHEY_PLAIN,1,yellow,1,cv2.LINE_AA)
        imgtoshow=cv2.add(imgt,imgtext)        
        imgtoshow=cv2.cvtColor(imgtoshow,cv2.COLOR_BGR2RGB)

        
        cv2.imshow('image',imgtoshow)

        if patchi :
            print 'retrieve patch asked', ix, iy
            imgtext=retrievepatch(ix,iy,top,slicenumber,preprob,listnamepatch)
            patchi=False

        if quitl or cv2.waitKey(20) & 0xFF == 27 :
#            print 'on quitte', quitl
            break
    quitl=False
#    print 'on quitte 2'
    cv2.destroyAllWindows()


def listfichier(dossier):
    Lf=[]
    L= os.listdir(dossier)
#    print L
    for k in L:
        if ".bmp" in k.lower(): 
            Lf.append(k)
    return Lf

def listbtn2(L,dirk,top):
    for widget in cadreim.winfo_children():
        widget.destroy()
    canvas = Canvas(cadreim, borderwidth=2, width=200,height=600,background="blue")
    frame = Frame(canvas, background="blue")
    vsb = Scrollbar(cadreim, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    canvas.pack(side="right", fill="both", expand=True)
    canvas.create_window((1,1), window=frame, anchor="nw")
#    canvas.create_window((1,1), window=frame)

    frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))
       
    for k in L: 
           Button(frame,text=k,command=lambda k = k:\
           openfichier(k,dirk,top,L)).pack(side=TOP,expand=1)

    
def opendir(k):
    global classdirec
#    
#    for widget in cadrepn.winfo_children():
#        widget.destroy()
    for widget in cadrestat.winfo_children():
        widget.destroy()
    Label(cadrestat, bg='lightgreen',text='patient:'+k).pack(side=TOP,fill=X,expand=1)
    tow=''
    fdir=os.path.join(path_patient,k)
    if classdirec==1:   
#        fdir=os.path.join(path_patient,k)
        bmp_dir = os.path.join(fdir, scanbmp)
    else:
        ldir=os.listdir(fdir)
        for ll in ldir:
             fdir = os.path.join(fdir, ll)
             bmp_dir = os.path.join(fdir, scanbmp)
    
    separator = Frame(cadrestat,height=2, bd=10, relief=SUNKEN)
    separator.pack(fill=X)
#    print 'bmp dir', bmp_dir      
    listscanfile =os.listdir(bmp_dir)
   
    ldcm=[]
    for ll in listscanfile:
      if  ll.lower().find('.bmp',0)>0:
         ldcm.append(ll)
    numberFile=len(ldcm)        
    tow='Number of sub sampled scan images: '+ str(numberFile)+\
    '\n\n'+'Predicted patterns: '+'\n' 
    for cle, valeur in listelabelfinal.items():
#             print 'cle valeur', cle,valeur
             for c in classif:
#                 print (k,c)
                 if (k,c) == cle and listelabelfinal[(k,c)]>0:

                     tow=tow+c+' : '+str(listelabelfinal[(k,c)])+'\n'

    Label(cadrestat, text=tow,bg='lightgreen').pack(side=TOP, fill='both',expand=1)
#    print tow
    dirkinter=os.path.join(fdir,predictout)
    dirk=os.path.join(dirkinter,vbg)
    L=listfichier(dirk)
    listbtn2(L,dirk,k)
    
       
def listdossier(dossier): 
    L= os.walk(dossier).next()[1]  
    return L
    
def listbtn(L):   
    cwt = Label(cadrerun,text="Select a patient")
    cwt.pack()
    for widget in cadrerun.winfo_children():       
                widget.destroy()    
    for k in L:
            Button(cadrerun,text=k,command=lambda k = k: opendir(k)).pack(side=LEFT,fill="both",\
            expand=1)

def runf():

    listbtn(listdossier( path_patient ))

    
def onFrameConfigure(canvas):
    '''Reset the scroll region to encompass the inner frame'''
    canvas.configure(scrollregion=canvas.bbox("all"))
    
    
def quit():
    global fenetre
    fenetre.quit()
    fenetre.destroy()   

def runpredict(pp,subs,thrp, thpro,retou):
    
    global classdirec,path_patient, patch_list, \
           dataset_list, nameset_list, proba,subsdef,varglobal,thrproba
    for widget in cadretop.winfo_children():       
                widget.destroy()    
    for widget in cadrelistpatient.winfo_children():
               widget.destroy()
    for widget in cadreparam.winfo_children():
               widget.destroy()
#    cadrestatus.grid(row=1)
    
    cw = Label(cadrestatus, text="Running",fg='red',bg='blue')
    cw.pack(side=TOP,fill=X)
    thrpatch=thrp
    thrproba=thpro
    subsdef =subs
    path_patient=pp
    varglobal=(thrpatch,thrproba,path_patient,subsdef)  
    newva()
    runl()
#    print path_patient
    if os.path.exists(path_patient):
       patient_list= os.walk(path_patient).next()[1]
       for f in patient_list:
            print('work on:',f, 'with subsamples :', subs)        
            namedirtopcf1 = os.path.join(path_patient,f)           
            listscanfile1= os.listdir(namedirtopcf1)
            for ll in listscanfile1:
                namedirtopcf=os.path.join(namedirtopcf1,ll)
                if os.path.isdir(namedirtopcf):
#                    print 'it is a dir'
                    listscanfile= os.listdir(namedirtopcf)
                    classdirec=2
        #    for ll in patient_list2:
                elif ll.find('.dcm',0)>0:
        #            print 'it is not a dir'
                    listscanfile=listscanfile1
                    namedirtopcf=namedirtopcf1
#                    print 'write classider'
                    classdirec=1
                    break
                
            ldcm=[]
            for ll in listscanfile:
             if  ll.lower().find('.dcm',0)>0:
                ldcm.append(ll)
            numberFile=len(ldcm)        
            if retou==1:
                patch_list=[]
                dataset_list=[]
                nameset_list=[]
                proba=[]
                
                #directory for scan in bmp
                bmp_dir = os.path.join(namedirtopcf, scanbmp)
                remove_folder(bmp_dir)    
                os.mkdir(bmp_dir) 
                #directory for lung mask
                lung_dir = os.path.join(namedirtopcf, lungmask)
                lung_bmp_dir = os.path.join(lung_dir, lungmaskbmp)
                if os.path.exists(lung_dir)== False:
                   os.mkdir(lung_dir)
                if os.path.exists(lung_bmp_dir)== False:
                   os.mkdir(lung_bmp_dir)
                   
                #directory for pickle from cnn and status
                pickledir = os.path.join( namedirtopcf,picklefile)             
                remove_folder(pickledir)
                os.mkdir(pickledir) 
                
                #directory for bpredicted images
                predictout_f_dir = os.path.join( namedirtopcf,predictout)
                remove_folder(predictout_f_dir)
                os.mkdir(predictout_f_dir)
                
                predictout_f_dir_bg = os.path.join( predictout_f_dir,vbg)
                remove_folder(predictout_f_dir_bg)
                os.mkdir(predictout_f_dir_bg)  
                
                predictout_f_dir_th = os.path.join( predictout_f_dir,str(thrproba))
                remove_folder(predictout_f_dir_th)
                os.mkdir(predictout_f_dir_th) 
                
                #directory for the pavaement in jpeg                
                jpegpathf = os.path.join( namedirtopcf,jpegpath)
                remove_folder(jpegpathf)    
                os.mkdir(jpegpathf)
                
#                subfile=os.path.join(pickledir,subsamplef)
#                subfilec = open(subfile, 'w')
#                subfilec.write('subsample '+str(subs)+'\n' )
#                subfilec.close()
                
                for scanumber in range(0,numberFile):
        #            print scanumber
                    if scanumber%subs==0:
#                        print 'loop',scanumber
                        scanfile=ldcm[scanumber]          
                        genebmp(namedirtopcf,scanfile,subs)
            
                                
                pavgene(namedirtopcf)
                ILDCNNpredict(namedirtopcf)
                visua(namedirtopcf,classdirec,True)   
                spkl=os.path.join(pickledir,subsamplef)
                pickle.dump(subs, open( spkl, "wb" ))
                
            else:                    
                visua(namedirtopcf,classdirec,False)
            print('completed on: ',f)     
       
       (top, tail)= os.path.split(path_patient)
       for widget in cadrestatus.winfo_children():       
                widget.destroy()
       wcadrewait = Label(cadrestatus, text="completed for "+tail,fg='darkgreen',bg='lightgreen',width=85)
       wcadrewait.pack()

       runf()
    else:
    #            print 'path patient does not exist'
        wer = Label(cadrestatus, text="path for patients does not exist",\
               fg='red',bg='yellow',width=85)
        wer.pack(side=TOP,fill='both')
        bouton1_run = Button(cadrestatus, text="continue", fg='red',\
              bg='yellow',command= lambda: runl1())
        bouton1_run.pack()


def runl1 ():
    for widget in cadrelistpatient.winfo_children():
               widget.destroy()
    for widget in cadreparam.winfo_children():
               widget.destroy()
    for widget in cadrestatus.winfo_children():
                widget.destroy()
    for widget in cadretop.winfo_children():
                widget.destroy()
    for widget in cadrerun.winfo_children():
                widget.destroy()
    for widget in cadrestat.winfo_children():
                widget.destroy()
    for widget in cadreim.winfo_children():
                widget.destroy()
#    for widget in cadrepn.winfo_children():
#                widget.destroy()
    runl()

def chp(newp):
    global varglobal
    varglobal=(thrpatch,thrproba,newp,subsdef)
    for widget in cadrelistpatient.winfo_children():
               widget.destroy()
    for widget in cadreparam.winfo_children():
               widget.destroy()
    for widget in cadrestatus.winfo_children():
                widget.destroy()
    for widget in cadretop.winfo_children():
                widget.destroy()
    for widget in cadrerun.winfo_children():
                widget.destroy()
    for widget in cadrestat.winfo_children():
                widget.destroy()
    for widget in cadreim.winfo_children():
                widget.destroy()
#    for widget in cadrepn.winfo_children():
#                widget.destroy()
   
#    print varglobal
    runl()




def runl ():
    global path_patient,varglobal
    runalready=False
#    print path_patient  varglobal=(thrpatch,thrproba,path_patient,subsdef)
    bouton_quit = Button(cadretop, text="Quit", command= quit,bg='red',fg='yellow')
    bouton_quit.pack(side="top")
    separator = Frame(cadretop,height=2, bd=10, relief=SUNKEN)
    separator.pack(fill=X)
    w = Label(cadretop, text="path for patients:")
    w.pack(side=LEFT,fill='both')
    
    clepp = StringVar()
    e = Entry(cadretop, textvariable=clepp,width=80)
    e.delete(0, END)
    e.insert(0, varglobal[2])
#    e.insert(0, workingdir)
    e.pack(side=LEFT,fill='both',expand=1)
    boutonp = Button(cadretop, text='change patient dir',command= lambda : chp(clepp.get()),bg='green',fg='blue')
    boutonp.pack(side=LEFT)
##   
#    print varglobal
    if os.path.exists(varglobal[2]):
        pl=os.listdir(varglobal[2])
        ll = Label(cadrelistpatient, text='list of patient(s):')
        ll.pack()
        tow=''
        for l in pl:
            ld=os.path.join(varglobal[2],l)
            if os.path.isdir(ld):
                tow =tow+l+' - '
                pdir=os.path.join(ld,picklefile)
                if os.path.exists(pdir):
                    runalready=True
                else:
                    psp=os.listdir(ld)
                    for ll in psp:
                        if ll.find('.dcm')<0:
                            pdir1=os.path.join(ld,ll)
                            pdir=os.path.join(pdir1,picklefile)
                            if os.path.exists(pdir):
                                runalready=True
                            
            ll = Label(cadrelistpatient, text=tow,fg='blue')
            
        ll.pack(side =TOP)
       
             

    else:     
        print 'do not exist'
        ll = Label(cadrelistpatient, text='path_patient does not exist:',fg='red',bg='yellow')
        ll.pack()

    separator = Frame(cadrelistpatient,height=2, bd=10, relief=SUNKEN)
    separator.pack(fill=X)

    wcadre5 = Label(cadreparam, text="subsample:")
    wcadre5.pack(side=LEFT)
    clev5 = IntVar()
    e5 = Entry(cadreparam, textvariable=clev5,width=5)
    e5.delete(0, END)
    e5.insert(0, str(varglobal[3]))
    e5.pack(fill='x',side=LEFT)
    wcadresep = Label(cadreparam, text=" | ",bg='purple')
    wcadresep.pack(side=LEFT)  

    wcadre6 = Label(cadreparam, text="patch ovelapp [0-1]:")
    wcadre6.pack(side=LEFT)    
    clev6 = DoubleVar()
    e6 = Entry(cadreparam, textvariable=clev6,width=5)
    e6.delete(0, END)
    e6.insert(0, str(varglobal[0]))    
    e6.pack(fill='x',side=LEFT)
    wcadresep = Label(cadreparam, text=" | ",bg='purple')
    wcadresep.pack(side=LEFT) 

    wcadre7 = Label(cadreparam, text="predict proba acceptance[0-1]:")
    wcadre7.pack(side=LEFT)
    clev7 = DoubleVar()
    e7 = Entry(cadreparam, textvariable=clev7,width=5)
    e7.delete(0, END)
    e7.insert(0, str(varglobal[1]))
    e7.pack(fill='x',side=LEFT)
    wcadresep = Label(cadreparam, text=" | ",bg='purple')   
    wcadresep.pack(side=LEFT)
    
#    retour0=IntVar(cadreparam)
#    bouton0 = Radiobutton(cadreparam, text='run predict',variable=retour0,value=1,bd=2)
#    bouton0.pack(side=RIGHT)
#    if runalready:
#         bouton1 = Radiobutton(cadreparam, text='visu only',variable=retour0,value=0,bd=2)
#         bouton1.pack(side=RIGHT)
#    print runalready
    if runalready:
       bouton_run1 = Button(cadreparam, text="Run visu", bg='green',fg='blue',\
             command= lambda: runpredict(clepp.get(),clev5.get(),clev6.get(),clev7.get(),0))
       bouton_run1.pack(side=RIGHT)
    bouton_run2 = Button(cadreparam, text="Run predict", bg='green',fg='blue',\
             command= lambda: runpredict(clepp.get(),clev5.get(),clev6.get(),clev7.get(),1))
    bouton_run2.pack(side=RIGHT)
#    separator = Frame(cadretop,height=2, bd=10, relief=SUNKEN)
#    separator.pack(fill=X, padx=5, pady=2)


##########################################################
    
t = datetime.datetime.now()
today = str('date: '+dd(t.month)+'-'+dd(t.day)+'-'+str(t.year)+\
'_'+dd(t.hour)+':'+dd(t.minute)+':'+dd(t.second))

print today


quitl=False
patchi=False
listelabelfinal={}
oldc=0
#imgtext = np.zeros((dimtabx,dimtaby,3), np.uint8)

fenetre = Tk()
fenetre.title("predict")
fenetre.geometry("700x800+100+50")



cadretop = LabelFrame(fenetre, width=700, height=20, text='top',borderwidth=5,bg="purple",fg='yellow')
cadretop.grid(row=0,sticky=NW)
cadrelistpatient = LabelFrame(fenetre, width=700, height=20, text='list',borderwidth=5,bg="purple",fg='yellow')
cadrelistpatient.grid(row=1,sticky=NW)
cadreparam = LabelFrame(fenetre, width=700, height=20, text='param',borderwidth=5,bg="purple",fg='yellow')
cadreparam.grid(row=2,sticky=NW)
cadrestatus = LabelFrame(fenetre,width=700, height=20,text="status run",bg='purple',fg='yellow')
cadrestatus.grid(row=3,sticky=NW)
cadrerun = LabelFrame(fenetre,text="select a patient",width=700, height=20,fg='yellow',bg='purple')
cadrerun.grid(row=4,sticky=NW)
#cadrepn = LabelFrame(fenetre,text="patient name list:",width=700, height=20,bg='purple',fg='yellow')
#cadrepn.grid(row=5,sticky=NW)
cadrestat=LabelFrame(fenetre,text="statistic", width=350,height=20,fg='yellow',bg='purple')
cadrestat.grid(row=6,  sticky=NW )
cadreim=LabelFrame(fenetre,text="images", width=350,height=20,fg='yellow',bg='purple')
cadreim.grid(row=6,  sticky=E)
    
#setva()
runl()

patch_list=[]
dataset_list=[]
nameset_list=[]
proba=[]
fenetre.mainloop()

#visuinter()
errorfile.close() 
