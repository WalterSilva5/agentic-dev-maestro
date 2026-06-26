import type { Type } from '@nestjs/common';
import { applyDecorators } from '@nestjs/common';
import {
  ApiResponseProperty,
  ApiExtraModels,
  ApiOkResponse,
  getSchemaPath,
  ApiProperty
} from '@nestjs/swagger';
import { Type as ClassTransformerType } from 'class-transformer';

class Meta {
  @ApiProperty({ default: 0 })
  @ClassTransformerType(() => Number)
  total: number;

  @ApiProperty({ default: null })
  @ClassTransformerType(() => undefined)
  lastPage: number;

  @ApiProperty({ default: 1 })
  @ClassTransformerType(() => Number)
  currentPage: number;

  @ApiProperty({ default: 10 })
  @ClassTransformerType(() => Number)
  perPage: number;

  @ApiProperty({ default: null })
  @ClassTransformerType(() => undefined)
  prev: number | null;

  @ApiProperty({ default: null })
  @ClassTransformerType(() => undefined)
  next: number | null;
}

export class Paginated<T> {
  @ApiProperty()
  data: T[];

  @ApiResponseProperty()
  meta: Meta;
}

export const ApiOkResponsePaginated = <DataDto extends Type<unknown>>(dataDto: DataDto) =>
  applyDecorators(
    ApiExtraModels(Paginated, dataDto),
    ApiOkResponse({
      schema: {
        allOf: [
          { $ref: getSchemaPath(Paginated) },
          {
            properties: {
              data: {
                type: 'array',
                items: { $ref: getSchemaPath(dataDto) }
              }
            }
          }
        ]
      }
    })
  );
