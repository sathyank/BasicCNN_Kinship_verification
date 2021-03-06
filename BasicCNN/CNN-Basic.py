import torch
import torch.nn as nn
from torch.autograd import Variable
from torch.utils.data import Dataset, DataLoader, sampler
import torchvision.transforms as transforms
import torch.nn.functional as F
from torch.optim import lr_scheduler
import numpy as np
import pandas as pd
from pandas.io.parsers import read_csv
from sklearn.utils import shuffle
from functools import wraps
from collections import OrderedDict
from sklearn.base import clone
from skimage import io
from skimage.color import rgb2gray
import matplotlib.pyplot as plt
import random
import time
import sys
import scipy.io as sio
import os
from pathlib import Path
import torchvision


rgb2gray = transforms.Compose([transforms.ToPILImage(),transforms.Grayscale(3),transforms.ToTensor()])
hf = transforms.Compose([transforms.ToPILImage(),transforms.RandomHorizontalFlip(),transforms.ToTensor()])
vf = transforms.Compose([transforms.ToPILImage(),transforms.RandomVerticalFlip(),transforms.ToTensor()])

class KinShipDataSet(Dataset):

    image_path = os.path.join(str(Path.home()), '/home/sathyank/Documents/PROJECT/images/KinFaceW-II/images')
    meta_data_path = os.path.join(str(Path.home()), '/home/sathyank/Documents/PROJECT/images/KinFaceW-II/meta_data/')
    rel_lookup = {'fd':'father-dau', 'fs':'father-son', 'md':'mother-dau', 'ms':'mother-son', 'all':'all'}

    def __init__(self, relation, transform = None, test = False, fold = 0,aug = False):
        self.meta_data =  sio.loadmat(os.path.join(KinShipDataSet.meta_data_path, relation + '_pairs.mat'))
        self.relation = relation
        self.transform = transform
        self.test = test
        self.fold = fold
        self.aug = aug
        self.trainlen = len([d for d in self.meta_data['pairs'][:, 0] if d != self.fold])
        self.testlen = len([d for d in self.meta_data['pairs'][:, 0] if d == self.fold])

    def __len__(self):

        if not self.test:
            return self.trainlen
        else:
            return self.testlen

    def __getitem__(self, i):

        #assert(i < len(self))

        if self.test:
            i += self.trainlen

        folder = KinShipDataSet.rel_lookup[self.meta_data['pairs'][i, 2][0][:2]]
        image_file1 = os.path.join(KinShipDataSet.image_path,  folder + '/' + self.meta_data['pairs'][i, 2][0])
        image_file2 = os.path.join(KinShipDataSet.image_path, folder + '/' + self.meta_data['pairs'][i, 3][0])
        #image1 = io.imread(image_file1).astype(np.float32)
        #image2 = io.imread(image_file2).astype(np.float32)
        image1 = io.imread(image_file1)
        image2 = io.imread(image_file2)
        gray1 = rgb2gray(image1)
        gray2 = rgb2gray(image2)
        #image1 = image1.transpose(2, 0, 1) #/ 255
        #image2 = image2.transpose(2, 0, 1) #/ 255
        if self.transform:
            image1 = self.transform(image1)
            #image1 = torch.from_numpy(image1.copy())
            image2 = self.transform(image2)
            #image2 = torch.from_numpy(image2.copy())

        else:
            image1 = torch.from_numpy(image1)
            image2 = torch.from_numpy(image2)
        #print(image1.shape)
        if self.test:
            if self.aug:
                vf1 = vf(image1)
                vf2 = vf(image2)
                hf1 = hf(image1)
                hf2 = hf(image2)

                pair_normal = torch.cat((image1, image2), dim = 0).view(-1,6,64,64)
                pair_gray = torch.cat((gray1,gray2),dim=0).view(-1,6,64,64)
                pair_hf = torch.cat((hf1,hf2),dim=0).view(-1,6,64,64)
                pair_vf = torch.cat((vf1,vf2),dim=0).view(-1,6,64,64)
                #pair = pair.view(-1,6,64,64)
                #print(pair.shape)
                pair = torch.cat((pair_normal,pair_gray,pair_hf,pair_vf),dim=0)
                #print(pair.shape)
                label = torch.LongTensor(np.full((4),int(self.meta_data['pairs'][i, 1]),dtype=int).tolist())
                sample = {'pair':pair, 'label':label}
            else:
                pair = torch.cat((image1, image2), dim = 0)
                label = torch.LongTensor([int(self.meta_data['pairs'][i, 1])])
                sample = {'pair':pair, 'label':label}
        else:
            if self.aug:
                vf1 = vf(image1)
                vf2 = vf(image2)
                hf1 = hf(image1)
                hf2 = hf(image2)

                pair_normal = torch.cat((image1, image2), dim = 0).view(-1,6,64,64)
                pair_gray = torch.cat((gray1,gray2),dim=0).view(-1,6,64,64)
                pair_hf = torch.cat((hf1,hf2),dim=0).view(-1,6,64,64)
                pair_vf = torch.cat((vf1,vf2),dim=0).view(-1,6,64,64)
                #pair = pair.view(-1,6,64,64)
                #print(pair.shape)
                pair = torch.cat((pair_normal,pair_gray,pair_hf,pair_vf),dim=0)
                #print(pair.shape)
                label = torch.LongTensor(np.full((4),int(self.meta_data['pairs'][i, 1]),dtype=int).tolist()) #if not self.test else None
                sample = {'pair':pair, 'label':label}
            else:
                pair = torch.cat((image1, image2), dim = 0).view(-1,6,64,64)
                label = torch.LongTensor([int(self.meta_data['pairs'][i, 1])])
                sample = {'pair':pair, 'label':label}
        return sample


def train_valid_split(length, test_size = 0.2, shuffle = False, random_seed = 0):
    """ Return a list of splitted indices from a DataSet.
    Indices can be used with DataLoader to build a train and validation set.

    Arguments:
        A Dataset
        A test_size, as a float between 0 and 1 (percentage split) or as an int (fixed number split)
        Shuffling True or False
        Random seed
    """
    #length = len(dataset)
    indices = list(range(0,length))

    if shuffle == True:
        random.seed(random_seed)
        random.shuffle(indices)

    if type(test_size) is float:
        split = int(test_size * length)
    elif type(test_size) is int:
        split = test_size
    else:
        raise ValueError('%s should be an int or a float' % str)

    return indices[split:], indices[:split]

def load(nsamples, relation, data_transforms,aug,fold,test_split = 0.2, test = False, batch_size = 32):
    if not test:
        # Creating a validation split
        train_idx, valid_idx = train_valid_split(nsamples, test_split, shuffle = True)
        train_sampler = sampler.SubsetRandomSampler(train_idx)
        valid_sampler = sampler.SubsetRandomSampler(valid_idx)
        #assert(data_transforms['train'] != None)
        #assert(data_transforms['val'] != None)
        x_train = KinShipDataSet(relation, data_transforms['train'], test=test,fold=fold,aug=aug)
        x_valid = KinShipDataSet(relation, data_transforms['val'], test=test,fold=fold,aug=aug)
        train_loader = DataLoader(x_train,
                      batch_size=batch_size,
                      sampler=train_sampler,
                      num_workers=8)
        valid_loader = DataLoader(x_valid,
                      batch_size=batch_size,
                      sampler=valid_sampler,
                      num_workers=8)

        dataloaders = {'train':train_loader, 'valid':valid_loader}
        dataset_sizes = {'train':len(train_sampler), 'valid':len(valid_sampler)}
        print(dataset_sizes)

    else:
        #assert(data_transforms['test'] != None)
        x_test = KinShipDataSet(relation, data_transforms['test'], test=test,fold=fold,aug=aug)
        test_loader = DataLoader(x_test, batch_size = batch_size)
        dataloaders = {'test':test_loader}
        dataset_sizes = {'test' : len(x_test)}
    return dataloaders, dataset_sizes

class ModelBasic_vanilla(nn.Module):

    def __init__(self):

        super().__init__()
        self.conv1 = nn.Conv2d(6, 16, 5)
        #self.bn1 = nn.BatchNorm2d(16)
        self.act1_c = nn.ReLU()
        self.pool1 = nn.MaxPool2d(2, stride = 2)
        self.conv2 = nn.Conv2d(16, 64, 5)
        #self.bn2 = nn.BatchNorm2d(64)
        self.act2_c = nn.ReLU()
        self.pool2 = nn.MaxPool2d(2, stride = 2)
        self.conv3 = nn.Conv2d(64, 128, 5)
        #self.bn3 = nn.BatchNorm2d(128)
        self.act3_c = nn.ReLU()
        self.fc1 = nn.Linear(128 * 9 * 9, 640)#self.fc1 = nn.Linear(128 * 9 * 9, 640)
        #self.bn4 = nn.BatchNorm2d(640)
        self.act1_f = nn.ReLU()
        self.fc2 = nn.Linear(640, 2)

    def forward(self, x):
        #print(x.data.shape)
        x = self.pool1(self.act1_c((self.conv1(x))))
        x = self.pool2(self.act2_c((self.conv2(x))))
        x = self.act3_c((self.conv3(x)))
        x = x.view(-1, 128 * 9 * 9)
        x = self.act1_f(self.fc1(x))
        x = self.fc2(x)
        return x

class ModelBasic_fbn(nn.Module):

    def __init__(self):

        super().__init__()
        self.conv1 = nn.Conv2d(6, 16, 5)
        self.bn1 = nn.BatchNorm2d(16)
        self.act1_c = nn.ReLU()
        self.pool1 = nn.MaxPool2d(2, stride = 2)
        self.conv2 = nn.Conv2d(16, 64, 5)
        self.bn2 = nn.BatchNorm2d(64)
        self.act2_c = nn.ReLU()
        self.pool2 = nn.MaxPool2d(2, stride = 2)
        self.conv3 = nn.Conv2d(64, 128, 5)
        self.bn3 = nn.BatchNorm2d(128)
        self.act3_c = nn.ReLU()
        self.fc1 = nn.Linear(128 * 9 * 9, 640)#self.fc1 = nn.Linear(128 * 9 * 9, 640)
        self.bn4 = nn.BatchNorm2d(640)
        self.act1_f = nn.ReLU()
        self.fc2 = nn.Linear(640, 2)

    def forward(self, x):
        #print(x.data.shape)
        x = self.pool1(self.act1_c(self.bn1(self.conv1(x))))
        x = self.pool2(self.act2_c(self.bn2(self.conv2(x))))
        x = self.act3_c(self.bn3(self.conv3(x)))
        x = x.view(-1, 128 * 9 * 9)
        x = self.act1_f(self.bn4(self.fc1(x)))
        x = self.fc2(x)
        return x
class AdjustVariable(object):

    def __init__(self, name, start = 0.9, stop = 0.999, num_epochs = 30):
        self.name = name
        self.start, self.stop = start, stop
        self.num_epochs = num_epochs
        self.ls = None

    def __call__(self, epoch):
        if self.ls is None:
            self.ls = np.linspace(self.start, self.stop, self.num_epochs)
        new_value = float(self.ls[epoch])
        return new_value

def train_model(model, dataloaders, dataset_sizes, criterion, optimizer,
                        scheduler = None, linear_momentum = False, early_stop = False):

    since = time.time()
    valid_loss_history = []
    train_loss_history = []
    num_epochs = model.num_epochs
    adjust_momentum = AdjustVariable('momentum', 0.9, 0.999, num_epochs)
    for epoch in range(num_epochs):

        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)
        total = 0
        correct = 0
        for phase in ['train', 'valid']:

            if phase == 'train':
                model.train(True)
                if scheduler:
                    scheduler.step()
                if linear_momentum:
                    new_momentum = adjust_momentum(epoch)
                    for param_groups in optimizer.param_groups:
                        param_groups['momentum'] = new_momentum
            else:
                model.train(False)

            running_loss = 0.0

            # Iterate over data.
            for data in dataloaders[phase]:
                # get the inputs
                inputs = data['pair'].view(-1,6,64,64)
                gt = data['label'].view(-1)
                if torch.cuda.is_available():
                    inputs, gt = Variable(inputs).cuda(), Variable(gt).cuda()
                else:
                    inputs, gt = Variable(inputs), Variable(gt)
                optimizer.zero_grad()
                #print(inputs.data.shape)
                outputs = model(inputs)
                loss = criterion(outputs, gt)
                if phase == 'train':
                    loss.backward()
                    optimizer.step()

                # statistics
                running_loss += loss.data[0]

            #epoch_loss = running_loss / (dataset_sizes[phase]*4)
            if phase == 'train':
                epoch_loss = running_loss / len(dataloaders[phase])
                train_loss_history.append(epoch_loss)

            else:
                #outputs = model(inputs)
                _, preds = torch.max(outputs.data, 1)
                total += gt.data.size(0)
                correct += (preds == gt.data).sum()
                epoch_loss = running_loss / len(dataloaders[phase])
                valid_loss_history.append(epoch_loss)
            print('{} Loss: {:.8f}'.format(
                    phase, epoch_loss))
            if phase == 'valid':
                print('Train Loss / Valid Loss: {:.6f}'.format(train_loss_history[-1] / valid_loss_history[-1]))
                print('Accuracy on validation set: %d %%' % (100 * correct / total))
                if early_stop:
                    EarlyStopping(patience = 200)
    loss_history = (train_loss_history, valid_loss_history)
    #model.register_buffer('loss_history', torch.Tensor(loss_history))
    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
                time_elapsed // 60, time_elapsed % 60))
    #torch.save(model.state_dict(), save_file)
    #torch.save(loss_history, save_file + '_loss_history')
    return model

def init_params(model):

    for m in model.children():
        for name, param in m.named_parameters():
            if name in ['weight']:
                nn.init.normal(param, 0, 0.01)
            if name in ['bias']:
                nn.init.constant(param, 0)

data_transforms = {
    'train':transforms.Compose([transforms.ToTensor()]),
    'val': transforms.Compose([transforms.ToTensor()]),
    'test': transforms.Compose([transforms.ToTensor()])
}

for fold in range(1,6):
    dataloaders, dataset_sizes = load(400,'md',data_transforms,True,fold,test_split=0.03,batch_size=32)
    model = ModelBasic_fbn()
    init_params(model)
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=0.005)
    exp_lr_scheduler = lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.95)
    model.num_epochs = 20
    if torch.cuda.is_available():
        model.cuda()
    model = train_model(model, dataloaders, dataset_sizes, criterion, optimizer,
                    scheduler = exp_lr_scheduler, linear_momentum = True, early_stop = False)
    correct = 0
    total = 0
    x_test = KinShipDataSet('md', data_transform, test=True,fold=fold,aug=False)
    test_loader = DataLoader(x_test,batch_size=32)
    for data in test_loader:
        inputs = data['pair'].view(-1,6,64,64)
        gt = data['label'].view(-1)
        if torch.cuda.is_available():
            inputs = Variable(inputs.cuda())
            gt = gt.cuda()
        else:
            inputs = Variable(inputs)
        #print(gt.shape)
        outputs = model(inputs)
        _, preds = torch.max(outputs.data, 1)

        total += gt.size(0)
        correct += (preds == gt).sum()

    print('Accuracy of the network on the test images: %d %%' % (100 * correct / total))
