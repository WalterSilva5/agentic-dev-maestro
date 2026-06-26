import { RegisterDto } from 'src/modules/auth/dto/register.dto';
import { JWTTokenDto } from 'src/modules/auth/dto/token.dto';
import { Test, TestingModule } from '@nestjs/testing';
import { faker } from '@faker-js/faker/locale/pt_BR';
import { PrismaClient, User } from '@prisma/client';
import { INestApplication } from '@nestjs/common';
import { AppModule } from '../src/app.module';
import { authenticateUser, createUser } from './shared';
import * as request from 'supertest';

describe('Auth module E2E Tests', () => {
  let app: INestApplication;
  let authData: JWTTokenDto;
  let userMock: RegisterDto;
  let user: User;

  beforeAll(async () => {
    const module: TestingModule = await Test.createTestingModule({
      imports: [AppModule]
    }).compile();

    app = module.createNestApplication();
    await app.init();

    [user, userMock] = await createUser();
  });

  afterAll(async () => {
    const prisma = new PrismaClient();
    try {
      await prisma.user.delete({
        where: {
          id: user?.id ?? 0
        }
      });
    } catch (_) {}

    await app.close();
  });

  it('Should log user in', async () => {
    authData = await authenticateUser(app, userMock);
  });

  it('Should not login for invalid user', async () => {
    await request(app.getHttpServer())
      .post('/auth/login')
      .send({
        email: faker.internet.email(),
        password: '12345'
      })
      .expect(401);
  });

  it('Should refresh user token', async () => {
    const response = await request(app.getHttpServer())
      .get('/auth/refresh')
      .set({ Authorization: `Bearer ${authData.refreshToken}` })
      .send({})
      .expect(200);

    expect(response.body).toHaveProperty('accessToken');
    expect(response.body).toHaveProperty('refreshToken');
    expect(response.body).toHaveProperty('user');

    authData = { ...authData, ...response.body };
  });

  it('Should log user out', async () => {
    await request(app.getHttpServer())
      .post('/auth/logout')
      .set({ Authorization: `Bearer ${authData.accessToken}` })
      .send()
      .expect(200);
  });

  it('Should invalidate last user session', async () => {
    if (process.env.PERMIT_DOUBLE_SESSION === 'true') {
      await request(app.getHttpServer())
        .post('/auth/logout')
        .set({ Authorization: `Bearer ${authData.accessToken}` })
        .send()
        .expect(200);
    } else {
      await request(app.getHttpServer())
        .post('/auth/logout')
        .set({ Authorization: `Bearer ${authData.accessToken}` })
        .send()
        .expect(401);
    }
  });
});
