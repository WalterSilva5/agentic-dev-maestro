import { JWTTokenDto } from 'src/modules/auth/dto/token.dto';
import { authenticateUser, createUser } from './shared';
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { AppModule } from '../src/app.module';
import { PrismaClient } from '@prisma/client';
import * as request from 'supertest';

describe('Auth module E2E Tests', () => {
  let app: INestApplication;
  let authData: JWTTokenDto;

  beforeAll(async () => {
    const module: TestingModule = await Test.createTestingModule({
      imports: [AppModule]
    }).compile();

    app = module.createNestApplication();
    await app.init();

    const [_, userMock] = await createUser();
    authData = await authenticateUser(app, userMock);
  });

  afterAll(async () => {
    const prisma = new PrismaClient();
    try {
      await prisma.user.delete({
        where: {
          id: authData?.user?.id ?? 0
        }
      });
    } catch (_) {}

    await app.close();
  });

  it('Should request user data', async () => {
    await request(app.getHttpServer())
      .get('/user/me')
      .set({ Authorization: `Bearer ${authData.accessToken}` })
      .send()
      .expect(200);
  });
});
