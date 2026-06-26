import {
  Controller,
  Get,
  Query,
  Param,
  ParseIntPipe,
  Body,
  Put,
  Delete,
  Post
} from '@nestjs/common';
import { ApiBearerAuth, ApiOkResponse, ApiTags } from '@nestjs/swagger';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import { Roles } from 'src/decorators/role.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import { Role } from 'src/enums/role.enum';
import { RoutesEnum } from 'src/enums/routes.enum';
import { DefaultFilter } from 'src/filters/DefaultFilter';
import type { Paginated } from 'src/interfaces/IPaginated';

import { User } from './entities/user.entity';
import { SimpleRegisterDto } from './models/simple-register.dto';
import { UserDto } from './models/user.dto';
import { UserService } from './user.service';

@ApiTags(RoutesEnum.USER)
@Controller(RoutesEnum.USER)
@ApiBearerAuth()
export class UserController {
  constructor(private readonly userService: UserService) {}

  @Post('register')
  @unprotected()
  @ApiOkResponse({ type: UserDto })
  async simpleRegister(@Body() dto: SimpleRegisterDto): Promise<User> {
    return this.userService.simpleRegister(dto);
  }

  @Get('me')
  @ApiBearerAuth()
  @ApiOkResponse({ type: UserDto })
  async getMe(@AuthenticatedUser() user: User): Promise<User> {
    return this.userService.getMe(user);
  }

  @Get('search')
  @ApiBearerAuth()
  @ApiOkResponse({ type: [UserDto] })
  async searchUsers(
    @Query('email') email?: string,
    @Query('q') query?: string,
  ): Promise<User[]> {
    // Support both 'email' (legacy) and 'q' (new) query parameters
    const searchTerm = query || email;
    return this.userService.searchUsers(searchTerm);
  }

  @Put('me')
  @ApiBearerAuth()
  @ApiOkResponse({ type: UserDto })
  async updateMe(@AuthenticatedUser() user: User, @Body() dto: UserDto): Promise<User> {
    return this.userService.updateMe(dto, user);
  }

  @Delete('me')
  @ApiBearerAuth()
  @ApiOkResponse({ type: UserDto })
  async deleteMe(@AuthenticatedUser() user: User): Promise<User> {
    return this.userService.deleteMe(user);
  }

  @Get()
  @ApiBearerAuth()
  @ApiOkResponse({ type: [UserDto] })
  @Roles(Role.ADMIN)
  protected async getFilteredAsync(
    @AuthenticatedUser() user: UserDto,
    @Query() filter: DefaultFilter
  ): Promise<Paginated<User>> {
    return this.userService.findFilteredAsync(filter, user);
  }

  @Get('/:id')
  @ApiOkResponse({ type: UserDto })
  @Roles(Role.ADMIN)
  protected async findByIdAsync(@Param('id', ParseIntPipe) id: number): Promise<User> {
    return this.userService.findById(id);
  }

  @Put('/:id')
  @Roles(Role.ADMIN)
  @ApiOkResponse({ type: UserDto })
  protected async updateAsync(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UserDto
  ): Promise<User> {
    return this.userService.updateAsync(id, dto);
  }

  @Delete('/:id')
  @Roles(Role.ADMIN)
  @ApiOkResponse({ type: UserDto })
  protected async deleteAsync(@Param('id', ParseIntPipe) id: number): Promise<User> {
    return this.userService.deleteAsync(id);
  }
}
