import { Injectable } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { DefaultFilter } from 'src/filters/DefaultFilter';
import type { Paginated } from 'src/interfaces/IPaginated';
import { Paginator } from 'src/utils/paginator';

import type { RegisterDto } from '../auth/dto/register.dto';
import type { User } from './entities/user.entity';
import type { UserDto } from './models/user.dto';

@Injectable()
export class UserRepository {
  constructor(private prisma: PrismaService) {}

  async getMe(idUser: number): Promise<User> {
    return this.prisma.user.findFirst({
      where: { id: idUser },
      include: { creditAccount: true }
    });
  }

  async create(dto: RegisterDto): Promise<User> {
    return this.prisma.user.create({
      data: {
        firstName: dto.firstName,
        lastName: dto.lastName,
        password: dto.password,
        email: dto.email
      }
    });
  }

  async findById(id: number): Promise<User> {
    return this.prisma.user.findFirst({
      where: { id },
      include: { creditAccount: true }
    });
  }

  async findByEmail(email: string): Promise<User> {
    return this.prisma.user.findFirst({
      where: { email },
      include: { creditAccount: true }
    });
  }

  async updateAsync(id: number, dto: UserDto): Promise<User> {
    // sanitize dto: remove fields that cannot be updated directly via Prisma `data`
    const {
      id: _id,
      createdAt: _createdAt,
      updatedAt: _updatedAt,
      deletedAt: _deletedAt,
      ...rest
    } = dto as unknown as Record<string, unknown>;

    // build data object removing undefined values
    const data = Object.fromEntries(
      Object.entries(rest).filter(([, v]) => v !== undefined)
    ) as Record<string, unknown>;

    // if birthDate is provided as string, convert to Date
    if (data.birthDate && typeof data.birthDate === 'string') {
      data.birthDate = new Date(data.birthDate as string);
    }

    return this.prisma.user.update({
      where: { id },
      data,
      include: { creditAccount: true }
    });
  }

  async findFilteredAsync(
    filter: DefaultFilter,
    _user?: UserDto
  ): Promise<Paginated<User>> {
    const OR: Array<Record<string, unknown>> = [];

    if (filter?.search) {
      ['firstName', 'lastName', 'email', 'username'].map((field: string) => {
        OR.push({
          [field]: {
            contains: filter.search
          }
        });
      });
    }

    const paginatedResult = await Paginator.applyPagination(this.prisma.user, {
      ...filter,
      where: {
        deletedAt: null,
        AND: {
          OR
        }
      }
    });

    this.filterPaginationFields(paginatedResult);

    return paginatedResult;
  }

  private filterPaginationFields(paginatedResult: { data: Array<Record<string, unknown>>; }) {
    paginatedResult.data = paginatedResult.data.map((user) => {
      const u = user as Record<string, unknown> & {
        id?: number;
        firstName?: string;
        lastName?: string;
        username?: string;
        email?: string;
        role?: unknown;
        gender?: unknown;
        birthDate?: unknown;
        creditAccount?: unknown;
      };

      return {
        id: u.id as number,
        firstName: u.firstName as string,
        lastName: u.lastName as string,
        username: u.username as string,
        email: u.email as string,
        role: u.role,
        gender: u.gender,
        birthDate: u.birthDate,
        creditAccount: u.creditAccount
      };
    });
  }

  public async deleteAsync(id: number): Promise<User> {
    return this.prisma.user.delete({
      where: { id }
    });
  }

  async searchUsers(query: string): Promise<User[]> {
    // Remove @ prefix if present for username search
    const searchTerm = query.startsWith('@') ? query.substring(1) : query;

    // MySQL LIKE is case-insensitive by default with utf8 collation
    return this.prisma.user.findMany({
      where: {
        OR: [
          {
            email: {
              contains: searchTerm,
            },
          },
          {
            username: {
              contains: searchTerm,
            },
          },
          {
            firstName: {
              contains: searchTerm,
            },
          },
          {
            lastName: {
              contains: searchTerm,
            },
          },
        ],
        deletedAt: null,
      },
      take: 10,
      include: { creditAccount: true },
    });
  }
}
