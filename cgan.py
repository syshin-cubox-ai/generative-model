from typing import Tuple

import numpy as np
import torch.backends.cudnn
import torch.nn as nn
import torch.utils.data

import common


class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(10, 10)
        self.model = nn.Sequential(
            nn.Linear(110, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 512),
            nn.LeakyReLU(0.2),
            nn.Linear(512, 1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 784),
            nn.Tanh(),
        )

    def forward(self, z, label):
        embed = self.embedding(label)
        x = torch.cat((z, embed), 1)
        x = self.model(x)
        return x


class Discriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(10, 10)
        self.model = nn.Sequential(
            nn.Linear(794, 1024),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, x, label):
        embed = self.embedding(label)
        x = torch.flatten(x, start_dim=1)
        x = torch.cat((x, embed), 1)
        x = self.model(x)
        return x


class CGAN(common.BaseGAN):
    def __init__(
            self,
            config: dict,
            generator: nn.Module,
            discriminator: nn.Module,
            z_dim: int,
    ):
        super().__init__(config, generator, discriminator, z_dim)

    def train_step(
            self,
            imgs: torch.Tensor,
            labels: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        imgs = imgs.to(self.device)
        labels = labels.to(self.device)
        real_labels = torch.ones((imgs.shape[0], 1), device=self.device)
        fake_labels = torch.zeros((imgs.shape[0], 1), device=self.device)

        # ???????????? real ???????????? real??? ???????????? loss ??????
        real_score = self.discriminator(imgs, labels)
        d_loss_real = self.criterion(real_score, real_labels)

        # ?????? ????????? fake ????????? ??????
        z = torch.randn((imgs.shape[0], self.z_dim), device=self.device)
        g_label = torch.randint(0, 10, (imgs.shape[0],)).to(self.device)
        sample_img = self.generator(z, g_label)

        # ???????????? fake ???????????? fake??? ???????????? loss ??????
        fake_score = self.discriminator(sample_img, g_label)
        d_loss_fake = self.criterion(fake_score, fake_labels)

        # real??? fake ???????????? ??? ????????? ????????? ?????? ????????? loss??? ??????
        d_loss = d_loss_real + d_loss_fake

        # ????????? ?????? ????????? ????????????
        self.d_optimizer.zero_grad(set_to_none=True)
        d_loss.backward()
        self.d_optimizer.step()

        # ???????????? ???????????? ??????????????? ?????? loss ??????
        deception_score = self.discriminator(self.generator(z, g_label), g_label)
        g_loss = self.criterion(deception_score, real_labels)

        # ????????? ?????? ????????? ????????????
        self.g_optimizer.zero_grad(set_to_none=True)
        g_loss.backward()
        self.g_optimizer.step()

        return d_loss, g_loss, real_score, fake_score

    def infer(self, num_rows: int) -> np.ndarray:
        self.generator.eval()

        z = torch.randn((num_rows * 10, self.z_dim), device=self.device)
        g_label = torch.tile(torch.arange(10, device=self.device), (num_rows,))
        with torch.no_grad():
            sample_img = self.generator(z, g_label)
        sample_img = self.post_process_sample_img(sample_img)
        return sample_img


if __name__ == '__main__':
    config = {
        'model_name': 'CGAN',
        'batch_size': 256,
        'epoch': 300,
        'lr': 0.0002,
        'reproducibility': True,
        'num_workers': 8,
        'pin_memory': True,
        'prefetch_factor': 60000,
        'persistent_workers': True,
    }

    # Model
    generator = Generator()
    discriminator = Discriminator()

    gan = CGAN(config, generator, discriminator, 100)
    if gan.select_training_or_demo() == 'Train':
        gan.train()
    else:
        gan.demo()
