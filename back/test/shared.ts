import { RegisterDto } from 'src/modules/auth/dto/register.dto';
import { JWTTokenDto } from 'src/modules/auth/dto/token.dto';
import { faker } from '@faker-js/faker/locale/pt_BR';
import { PrismaClient, User } from '@prisma/client';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import * as bcrypt from 'bcrypt';

export const getUserMock = (): RegisterDto => {
  return {
    password: faker.internet.password(),
    firstName: faker.name.firstName(),
    lastName: faker.name.lastName(),
    email: faker.internet.email()
  };
};


export const createUser = async (): Promise<[User, RegisterDto]> => {
  const userMock = getUserMock();

  const prisma = new PrismaClient();
  const user = await prisma.user.create({
    data: {
      password: await bcrypt.hash(userMock.password, 10),
      firstName: userMock.firstName,
      lastName: userMock.lastName,
      email: userMock.email
    }
  });

  return [user, userMock];
};

export const authenticateUser = async (
  app: INestApplication,
  userMock: RegisterDto
): Promise<JWTTokenDto> => {
  const response = await request(app.getHttpServer())
    .post('/auth/login')
    .send({ email: userMock.email, password: userMock.password })
    .expect(200);

  expect(response.body).toHaveProperty('accessToken');
  expect(response.body).toHaveProperty('refreshToken');
  expect(response.body).toHaveProperty('user');

  expect(response.body.user).not.toHaveProperty('sessionToken');
  expect(response.body.user).not.toHaveProperty('password');
  expect(response.body.user).toHaveProperty('createdAt');

  expect(response.body.user.firstName).toBe(userMock.firstName);
  expect(response.body.user.lastName).toBe(userMock.lastName);
  expect(response.body.user.email).toBe(userMock.email);

  return response.body;
};

export const validatePagination = (response: { body: any }) => {
  expect(response.body).toHaveProperty('meta');

  expect(response.body.meta).toHaveProperty('total');
  expect(response.body.meta).toHaveProperty('lastPage');
  expect(response.body.meta).toHaveProperty('currentPage');
  expect(response.body.meta).toHaveProperty('perPage');
  expect(response.body.meta).toHaveProperty('prev');
  expect(response.body.meta).toHaveProperty('next');

  expect(response.body).toHaveProperty('data');
  expect(response.body.data).toBeInstanceOf(Array);
};
