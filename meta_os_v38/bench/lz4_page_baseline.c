#define _POSIX_C_SOURCE 200809L
#include <lz4.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define PAGE 4096u
static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);return (uint64_t)t.tv_sec*1000000000ull+t.tv_nsec;}
static void mutate(uint8_t*p,size_t page_id,unsigned gen){if((page_id+gen)%3==0){size_t pos=((page_id*131u)+gen*17u)%PAGE;for(size_t i=0;i<16;++i)p[(pos+i)%PAGE]^=(uint8_t)(gen+i+1);}}
int main(int argc,char**argv){if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 2;fseek(f,0,SEEK_END);long sz=ftell(f);rewind(f);size_t pages=((size_t)sz+PAGE-1)/PAGE;uint8_t*src=calloc(pages,PAGE);uint8_t*out=malloc(PAGE);char*comp=malloc(LZ4_compressBound(PAGE));fread(src,1,(size_t)sz,f);fclose(f);uint64_t logical=0,stored=0,en=0,de=0;unsigned gens=4;for(unsigned g=0;g<gens;++g){if(g)for(size_t p=0;p<pages;++p)mutate(src+p*PAGE,p,g);for(size_t p=0;p<pages;++p){uint64_t t=ns();int n=LZ4_compress_default((char*)src+p*PAGE,comp,PAGE,LZ4_compressBound(PAGE));en+=ns()-t;if(n<=0)return 3;stored+=(uint64_t)n+32;logical+=PAGE;t=ns();int q=LZ4_decompress_safe(comp,(char*)out,n,PAGE);de+=ns()-t;if(q!=PAGE||memcmp(out,src+p*PAGE,PAGE))return 4;}}double mib=(double)logical/(1024.0*1024.0);printf("{\"logical_bytes\":%"PRIu64",\"physical_bytes_with_meta\":%"PRIu64",\"effective_ratio\":%.6f,\"encode_mib_s\":%.3f,\"decode_mib_s\":%.3f}\n",logical,stored,(double)logical/stored,mib/((double)en/1e9),mib/((double)de/1e9));free(src);free(out);free(comp);return 0;}
