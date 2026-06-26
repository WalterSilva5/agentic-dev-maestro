import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import * as bcrypt from 'bcrypt';
import { Messages } from 'src/enums/messages.enum';
import type { DefaultFilter } from 'src/filters/DefaultFilter';
import type { Paginated } from 'src/interfaces/IPaginated';
import type { ISensitiveData } from 'src/interfaces/ISensitiveData';
import type { RegisterDto } from 'src/modules/auth/dto/register.dto';
import { CreditAccountService } from 'src/modules/credit-account/credit-account.service';

import type { User } from './entities/user.entity';
import type { UserDto } from './models/user.dto';
import type { SimpleRegisterDto } from './models/simple-register.dto';
import { UserRepository } from './user.repository';

type Key = keyof User;

@Injectable()
export class UserService {
  constructor(
    private readonly userRepository: UserRepository,
    private readonly creditAccountService: CreditAccountService // injected for initial credits
  ) {}

  excludeUserFields(user: User, keys: Key[]): User {
    for (const key of keys) {
      delete user[key];
    }
    return user;
  }

  async getMe(dto: User): Promise<User> {
    return this.findById(dto.id);
  }

  async findByEmail(email: string, returningOptions?: ISensitiveData): Promise<User> {
    const user: User = await this.userRepository.findByEmail(email);
    if (!user) {
      return null;
    }

    const fieldsToExclude: Key[] = [];

    if (!returningOptions?.sessionToken) fieldsToExclude.push('sessionToken');
    if (!returningOptions?.password) fieldsToExclude.push('password');

    return this.excludeUserFields(user, fieldsToExclude);
  }

  async findById(idUser: number, returningOptions?: ISensitiveData): Promise<User> {
    const user: User = await this.userRepository.findById(idUser);

    if (!user) {
      return null;
    }

    const fieldsToExclude: Key[] = [];

    if (!returningOptions?.sessionToken) fieldsToExclude.push('sessionToken');
    if (!returningOptions?.password) fieldsToExclude.push('password');

    return this.excludeUserFields(user, fieldsToExclude);
  }

  async create(dto: RegisterDto): Promise<User> {
    const userAlreadyRegistered = await this.userRepository.findByEmail(dto.email);

    if (userAlreadyRegistered) {
      throw new BadRequestException(Messages.ALREADY_EXISTS_ONE_ACCOUNT_FOR_THIS_EMAIL);
    }

    if (dto.password) dto.password = await bcrypt.hash(dto.password, 10);
    const user = await this.userRepository.create(dto);

    // Sempre crie conta de crédito e conceda créditos iniciais
    await this.creditAccountService.addCredit({ userId: user.id, amount: 30 });

    return this.excludeUserFields(user, ['password', 'sessionToken']);
  }

  async findFilteredAsync(
    filter: DefaultFilter,
    user?: UserDto
  ): Promise<Paginated<User>> {
    return this.userRepository.findFilteredAsync(filter, user);
  }

  async updateAsync(id: number, dto: UserDto): Promise<User> {
    const user = await this.findById(id);
    if (!user) {
      throw new NotFoundException(Messages.USER_NOT_FOUND);
    }
    const updatedUser = await this.userRepository.updateAsync(id, dto);
    return this.excludeUserFields(updatedUser, ['password', 'sessionToken']);
  }

  async updateMe(dto: UserDto, user: User): Promise<User> {
    const existing = await this.findById(user.id);
    if (!existing) {
      throw new NotFoundException(Messages.USER_NOT_FOUND);
    }

    // Ensure users cannot change their role via this endpoint
    if (dto.role && dto.role !== existing.role) {
      dto.role = existing.role;
    }

    const updatedUser = await this.userRepository.updateAsync(user.id, dto);
    return this.excludeUserFields(updatedUser, ['password', 'sessionToken']);
  }

  async deleteMe(user: User): Promise<User> {
    const existing = await this.findById(user.id);
    if (!existing) {
      throw new NotFoundException(Messages.USER_NOT_FOUND);
    }

    const deletedUser = await this.userRepository.deleteAsync(user.id);
    return this.excludeUserFields(deletedUser, ['password', 'sessionToken']);
  }

  async deleteAsync(id: number): Promise<User> {
    const user = await this.findById(id);
    if (!user) {
      throw new NotFoundException(Messages.USER_NOT_FOUND);
    }
    const deletedUser = await this.userRepository.deleteAsync(id);
    return this.excludeUserFields(deletedUser, ['password', 'sessionToken']);
  }

  async simpleRegister(dto: SimpleRegisterDto): Promise<User> {
    const userAlreadyRegistered = await this.userRepository.findByEmail(dto.email);

    if (userAlreadyRegistered) {
      throw new BadRequestException(Messages.ALREADY_EXISTS_ONE_ACCOUNT_FOR_THIS_EMAIL);
    }

    const hashedPassword = await bcrypt.hash(dto.password, 10);

    const newUser = await this.userRepository.create({
      firstName: dto.firstName,
      lastName: dto.lastName,
      email: dto.email,
      password: hashedPassword
    });

    // Sempre crie conta de crédito e conceda créditos iniciais
    await this.creditAccountService.addCredit({ userId: newUser.id, amount: 30 });

    return this.excludeUserFields(newUser, ['password', 'sessionToken']);
  }

  async searchUsers(query: string): Promise<User[]> {
    if (!query || query.trim().length < 2) {
      return [];
    }

    const users = await this.userRepository.searchUsers(query.trim());
    return users.map(user => this.excludeUserFields(user, ['password', 'sessionToken']));
  }
}
