import { api } from './client'
import { photoMetaSchema, type PhotoMeta } from '../schemas/photo'

export type PhotoSize = '160' | '640' | 'full'

export function photoUrl(photoId: number, size: PhotoSize = '640'): string {
  return `/api/photos/${photoId}?size=${size}`
}

export type PhotoOwner =
  | { kind: 'piece'; pieceId: number }
  | { kind: 'stockLot'; inventoryId: number; lotId: number }
  | { kind: 'set'; setId: number }
  | { kind: 'materialType'; materialTypeId: number }
  | { kind: 'damage'; damageId: number }
  | { kind: 'inventory'; inventoryId: number }
  | { kind: 'loan'; loanId: number }

function uploadPath(owner: PhotoOwner): string {
  switch (owner.kind) {
    case 'piece':
      return `/api/pieces/${owner.pieceId}/photos`
    case 'stockLot':
      return `/api/inventories/${owner.inventoryId}/stock-lots/${owner.lotId}/photos`
    case 'set':
      return `/api/sets/${owner.setId}/photos`
    case 'materialType':
      return `/api/material-types/${owner.materialTypeId}/photos`
    case 'damage':
      return `/api/damages/${owner.damageId}/photos`
    case 'inventory':
      return `/api/inventories/${owner.inventoryId}/photos`
    case 'loan':
      return `/api/loans/${owner.loanId}/photos`
  }
}

export async function uploadPhoto(owner: PhotoOwner, file: Blob, fileName: string): Promise<PhotoMeta> {
  const form = new FormData()
  form.append('file', file, fileName.endsWith('.jpg') ? fileName : `${fileName}.jpg`)
  const response = await api.post(uploadPath(owner), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return photoMetaSchema.parse(response.data)
}

export async function deletePhoto(photoId: number): Promise<void> {
  await api.delete(`/api/photos/${photoId}`)
}

export async function makeCoverPhoto(photoId: number): Promise<PhotoMeta> {
  const response = await api.post(`/api/photos/${photoId}/make-cover`)
  return photoMetaSchema.parse(response.data)
}
